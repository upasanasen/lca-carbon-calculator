"""ÖKOBAUDAT live EPD adapter (soda4LCA REST API).

ÖKOBAUDAT is the German Federal Ministry's open EPD database. It exposes a
soda4LCA RESTful service that returns ILCD+EN 15804 datasets as JSON. Data is
public and free; no API key is required, which makes it the primary live
external EPD source for this app (works locally and on Streamlit Cloud).

API shape (confirmed against the live service):
  search : GET {BASE}/processes?format=JSON&search=true&name=<q>&pageSize=<n>
           -> {startIndex, pageSize, totalCount, data:[{name, uuid, geo,
               refYear, validUntil, classific, ...}]}
  detail : GET {BASE}/processes/{uuid}?format=JSON&view=extended
           -> {processInformation, exchanges, LCIAResults, ...}

GWP per module lives in LCIAResults.LCIAResult[]; the "GWP-total" indicator's
`other.anies` is a list of {"module": "A1-A3", "value": "12.97"} entries plus a
unit reference ("kg CO2 eq."). The declared/reference unit (per kg, m2, m3,
piece) is the reference flow's referenceFlowProperty.referenceUnit.

This adapter only takes A1-A3 and C1-C4 from the EPD. A4 (transport), A5
(wastage) and B6 (operational energy) are derived by the engine, so taking the
EPD's A4/A5/B6 here would double-count.

Endpoints/terms verified mid-2025; re-check against live docs before relying on
results externally.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

import requests

from .base import FactorAdapter, FactorCandidate
from ..models import EmissionFactorSet

DEFAULT_BASE_URL = "https://oekobaudat.de/OEKOBAU.DAT/resource"

# ÖKOBAUDAT / GaBi reference unit codes -> the engine's canonical units.
_UNIT_MAP = {
    "kg": "kg",
    "kilogram": "kg",
    "g": "g",
    "t": "t",
    "qm": "m2",
    "m^2": "m2",
    "m2": "m2",
    "m²": "m2",
    "cbm": "m3",
    "m^3": "m3",
    "m3": "m3",
    "m³": "m3",
    "stück": "each",
    "stk": "each",
    "piece": "each",
    "pieces": "each",
    "pcs": "each",
    "stk.": "each",
}


def _text(multilang: Any, prefer: str = "en") -> str:
    """Pull a string from an ILCD multilingual list like [{lang,value}, ...]."""
    if isinstance(multilang, str):
        return multilang
    if isinstance(multilang, list):
        by_lang = {item.get("lang"): item.get("value", "") for item in multilang if isinstance(item, dict)}
        return by_lang.get(prefer) or by_lang.get("en") or next(iter(by_lang.values()), "") if by_lang else ""
    return ""


def _canon(label: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (label or "").lower())


def _norm_unit(ref_unit: Optional[str]) -> str:
    if not ref_unit:
        return ""
    key = ref_unit.strip().lower()
    return _UNIT_MAP.get(key, ref_unit.strip())


def _to_float(value: Any) -> Optional[float]:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f


def _pick_gwp_result(results: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Choose the GWP-total indicator, with fallbacks for EN 15804+A1 data."""
    exclude = ("fossil", "biogenic", "luluc", "landuse", "land use")

    def label_of(r: Dict[str, Any]) -> str:
        ref = r.get("referenceToLCIAMethodDataSet", {}) or {}
        return _text(ref.get("shortDescription", []))

    # 1) explicit GWP-total
    for r in results:
        if "gwptotal" in _canon(label_of(r)):
            return r
    # 2) any GWP that is not a sub-component (handles +A1 single "GWP")
    for r in results:
        lab = label_of(r).lower()
        if "gwp" in _canon(label_of(r)) and not any(x in lab for x in exclude):
            return r
    return None


def parse_process(detail: Dict[str, Any], record_id: str, base_url: str = DEFAULT_BASE_URL) -> EmissionFactorSet:
    """Parse a soda4LCA extended process JSON into an EmissionFactorSet.

    Kept as a module-level function (no network) so it is unit-testable with a
    captured fixture.
    """
    # --- reference flow: declared unit + name + density ---
    declared_unit = "kg"
    material_name = ""
    density_kg_per_m3: Optional[float] = None

    pi = detail.get("processInformation", {}) or {}
    qr = pi.get("quantitativeReference", {}) or {}
    ref_ids = qr.get("referenceToReferenceFlow") or []
    ref_id = ref_ids[0] if ref_ids else None

    exchanges = (detail.get("exchanges", {}) or {}).get("exchange", []) or []
    ref_exchange = None
    for ex in exchanges:
        if ex.get("dataSetInternalID") == ref_id or ex.get("referenceFlow") is True:
            ref_exchange = ex
            break
    if ref_exchange is None and exchanges:
        ref_exchange = exchanges[0]

    mass_per_unit: Optional[float] = None
    if ref_exchange:
        material_name = _text(ref_exchange.get("referenceToFlowDataSet", {}).get("shortDescription", []))
        for fp in ref_exchange.get("flowProperties", []) or []:
            name = _text(fp.get("name", [])).lower()
            if fp.get("referenceFlowProperty") is True:
                declared_unit = _norm_unit(fp.get("referenceUnit")) or declared_unit
            if name == "mass" or "masse" in name:
                mass_per_unit = _to_float(fp.get("meanValue"))
        if mass_per_unit and declared_unit == "m3":
            density_kg_per_m3 = mass_per_unit  # kg per 1 m3

    # --- GWP per module ---
    gwp = {"A1A3": 0.0, "A4": 0.0, "A5": 0.0, "B6": 0.0, "C1": 0.0, "C2": 0.0, "C3": 0.0, "C4": 0.0}
    results = (detail.get("LCIAResults", {}) or {}).get("LCIAResult", []) or []
    gwp_result = _pick_gwp_result(results)
    indicator_label = ""
    if gwp_result:
        ref = gwp_result.get("referenceToLCIAMethodDataSet", {}) or {}
        indicator_label = _text(ref.get("shortDescription", []))
        anies = (gwp_result.get("other", {}) or {}).get("anies", []) or []
        a123_parts = {}
        for entry in anies:
            module = entry.get("module")
            value = _to_float(entry.get("value"))
            if not module or value is None:
                continue
            m = module.upper().replace(" ", "")
            if m in ("A1-A3", "A1A3"):
                gwp["A1A3"] += value
            elif m in ("A1", "A2", "A3"):
                a123_parts[m] = value
            elif m in ("C1", "C2", "C3", "C4"):
                gwp[m] += value
            # A4/A5/B6/B*/D intentionally ignored (engine derives or out of scope)
        if gwp["A1A3"] == 0.0 and a123_parts:
            gwp["A1A3"] = sum(a123_parts.values())

    geo = (pi.get("geography", {}) or {}).get("locationOfOperationSupplyOrProduction", {}).get("location", "")
    valid_until = ""
    pub = (pi.get("time", {}) or {})
    valid_until = str(pub.get("referenceYear", "") or "")

    citation = (
        f"ÖKOBAUDAT EPD: {material_name or record_id} (UUID {record_id}). "
        f"Indicator: {indicator_label or 'GWP'}. Source: ÖKOBAUDAT / soda4LCA, {base_url}. "
        "Verify validity date and declared unit against the source dataset."
    )

    fs = EmissionFactorSet(
        record_id=record_id,
        source="ÖKOBAUDAT (soda4LCA)",
        source_type="epd",
        declared_unit=declared_unit,
        gwp_by_module=gwp,
        material_name=material_name or record_id,
        geography=geo or "DE/EU",
        valid_until=valid_until,
        citation=citation,
        data_quality="epd",
        notes="A1-A3 and C1-C4 taken from EPD; A4/A5/B6 derived by the engine.",
    )
    # stash density for the UI to use as a default (optional, non-model attr)
    fs.__dict__["density_kg_per_m3_hint"] = density_kg_per_m3
    return fs


class OkobaudatAdapter(FactorAdapter):
    name = "okobaudat"

    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout: int = 15) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _get_json(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        resp = requests.get(url, params=params, timeout=self.timeout, headers={"Accept": "application/json"})
        resp.raise_for_status()
        return resp.json()

    def search(self, query: str, limit: int = 20) -> List[FactorCandidate]:
        data = self._get_json(
            "processes",
            {"format": "JSON", "search": "true", "name": query or "", "pageSize": max(1, limit)},
        )
        candidates: List[FactorCandidate] = []
        for row in data.get("data", [])[:limit]:
            name = row.get("name") or row.get("uuid", "")
            geo = row.get("geo", "")
            ref_year = row.get("refYear", "")
            candidates.append(
                FactorCandidate(
                    record_id=row.get("uuid", ""),
                    material_name=name,
                    declared_unit="(load to resolve)",
                    source="ÖKOBAUDAT (soda4LCA)",
                    source_type="epd",
                    geography=geo,
                    citation=f"ÖKOBAUDAT {ref_year} · {geo}".strip(" ·"),
                    preview_gwp_a1a3=0.0,  # resolved on get(); avoids N detail calls during search
                )
            )
        return candidates

    def total_count(self, query: str) -> int:
        data = self._get_json(
            "processes", {"format": "JSON", "search": "true", "name": query or "", "pageSize": 1}
        )
        return int(data.get("totalCount", 0))

    def get(self, record_id: str) -> EmissionFactorSet:
        detail = self._get_json(f"processes/{record_id}", {"format": "JSON", "view": "extended"})
        return parse_process(detail, record_id=record_id, base_url=self.base_url)
