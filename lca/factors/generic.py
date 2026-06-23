from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .base import FactorAdapter, FactorCandidate
from ..models import EmissionFactorSet


DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "generic_factors.csv"


def _float(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


class GenericFactorAdapter(FactorAdapter):
    name = "generic"

    def __init__(self, data_path: Optional[Path] = None) -> None:
        self.data_path = data_path or DATA_PATH
        self._records = self._load()

    def _load(self) -> Dict[str, Dict[str, str]]:
        records: Dict[str, Dict[str, str]] = {}
        with self.data_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                records[row["record_id"]] = row
        return records

    def all_records(self) -> Iterable[Dict[str, str]]:
        return self._records.values()

    def search(self, query: str, limit: int = 20) -> List[FactorCandidate]:
        needle = (query or "").strip().lower()
        rows = list(self._records.values())
        if needle:
            rows = [
                row
                for row in rows
                if needle in row["material_name"].lower() or needle in row.get("keywords", "").lower()
            ]
        rows = sorted(rows, key=lambda row: row["material_name"])[:limit]
        return [
            FactorCandidate(
                record_id=row["record_id"],
                material_name=row["material_name"],
                declared_unit=row["declared_unit"],
                source=row["source"],
                source_type="generic",
                geography=row.get("geography", ""),
                citation=row.get("citation", ""),
                preview_gwp_a1a3=_float(row.get("A1A3", "0")),
            )
            for row in rows
        ]

    def get(self, record_id: str) -> EmissionFactorSet:
        row = self._records[record_id]
        return EmissionFactorSet(
            record_id=row["record_id"],
            source=row["source"],
            source_type="generic",
            declared_unit=row["declared_unit"],
            material_name=row["material_name"],
            geography=row.get("geography", "Global"),
            valid_until=row.get("valid_until", ""),
            citation=row.get("citation", ""),
            data_quality=row.get("data_quality", "screening"),
            notes=row.get("notes", ""),
            gwp_by_module={
                "A1A3": _float(row.get("A1A3", "0")),
                "A4": 0.0,
                "A5": 0.0,
                "B6": 0.0,
                "C1": _float(row.get("C1", "0")),
                "C2": _float(row.get("C2", "0")),
                "C3": _float(row.get("C3", "0")),
                "C4": _float(row.get("C4", "0")),
            },
        )

    def defaults_for(self, record_id: str) -> Dict[str, Optional[float]]:
        row = self._records[record_id]
        return {
            "density_kg_per_m3": _float(row.get("density_kg_per_m3", ""), 0.0) or None,
            "wastage_rate": _float(row.get("default_wastage_rate", ""), 0.0),
        }
