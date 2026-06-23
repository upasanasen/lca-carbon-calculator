from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4


MODULES = ("A1A3", "A4", "A5", "B6", "C1", "C2", "C3", "C4")
EMBODIED_MODULES = ("A1A3", "A4", "A5", "C1", "C2", "C3", "C4")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:10]}"


def module_dict(default: float = 0.0) -> Dict[str, float]:
    return {module: default for module in MODULES}


@dataclass
class EmissionFactorSet:
    record_id: str
    source: str
    source_type: str
    declared_unit: str
    gwp_by_module: Dict[str, float]
    material_name: str = ""
    geography: str = "Global"
    valid_until: str = ""
    citation: str = ""
    data_quality: str = "screening"
    notes: str = ""

    def factor(self, module: str) -> float:
        return float(self.gwp_by_module.get(module, 0.0) or 0.0)

    @classmethod
    def empty(cls, material_name: str = "") -> "EmissionFactorSet":
        return cls(
            record_id="manual-empty",
            source="manual",
            source_type="override",
            declared_unit="kg",
            gwp_by_module=module_dict(),
            material_name=material_name,
            citation="User supplied values required.",
            data_quality="manual",
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmissionFactorSet":
        values = dict(data)
        values["gwp_by_module"] = {
            module: float(values.get("gwp_by_module", {}).get(module, 0.0) or 0.0)
            for module in MODULES
        }
        return cls(**values)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LineItem:
    material_name: str
    quantity: float
    unit: str
    factor: EmissionFactorSet
    element_name: str = "Unassigned"
    category: str = "Other"
    id: str = field(default_factory=lambda: new_id("line"))
    density_kg_per_m3: Optional[float] = None
    transport_distance_km: Optional[float] = None
    transport_mode: str = "road"
    wastage_rate: Optional[float] = None
    notes: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LineItem":
        values = dict(data)
        values["factor"] = EmissionFactorSet.from_dict(values["factor"])
        for key in ("quantity", "density_kg_per_m3", "transport_distance_km", "wastage_rate"):
            if values.get(key) in ("", None):
                values[key] = None if key != "quantity" else 0.0
            else:
                values[key] = float(values[key])
        return cls(**values)

    def to_dict(self) -> Dict[str, Any]:
        values = asdict(self)
        values["factor"] = self.factor.to_dict()
        return values


@dataclass
class Project:
    name: str
    building_type: str = "Office"
    gross_floor_area_m2: float = 1000.0
    study_period_years: int = 60
    location: str = "Unspecified"
    id: str = field(default_factory=lambda: new_id("project"))
    dataset_version: str = "generic-seed-2026-06"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat(timespec="seconds"))
    default_transport_distance_km: float = 50.0
    annual_energy_kwh: Optional[float] = None
    energy_intensity_kwh_m2yr: Optional[float] = None
    grid_emission_factor_kgco2e_kwh: float = 0.0
    grid_factor_source: str = "Unset. Enter a sourced grid factor before using B6 results."
    line_items: List[LineItem] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Project":
        values = dict(data)
        values["line_items"] = [LineItem.from_dict(item) for item in values.get("line_items", [])]
        for key in (
            "gross_floor_area_m2",
            "default_transport_distance_km",
            "annual_energy_kwh",
            "energy_intensity_kwh_m2yr",
            "grid_emission_factor_kgco2e_kwh",
        ):
            if values.get(key) in ("", None):
                values[key] = None if key in ("annual_energy_kwh", "energy_intensity_kwh_m2yr") else 0.0
            else:
                values[key] = float(values[key])
        values["study_period_years"] = int(values.get("study_period_years", 60) or 60)
        return cls(**values)

    def to_dict(self) -> Dict[str, Any]:
        values = asdict(self)
        values["line_items"] = [item.to_dict() for item in self.line_items]
        return values


@dataclass
class ResultRow:
    line_item_id: str
    material_name: str
    element_name: str
    category: str
    quantity: float
    unit: str
    declared_quantity: float
    declared_unit: str
    mass_kg: Optional[float]
    source_type: str
    source: str
    citation: str
    module_gwps: Dict[str, float]
    total_gwp: float
    warnings: List[str] = field(default_factory=list)
    excluded: bool = False

    def to_dict(self) -> Dict[str, Any]:
        values = asdict(self)
        for module in MODULES:
            values[module] = self.module_gwps.get(module, 0.0)
        return values


@dataclass
class ProjectResult:
    project_id: str
    project_name: str
    rows: List[ResultRow]
    module_totals: Dict[str, float]
    element_totals: Dict[str, float]
    category_totals: Dict[str, float]
    embodied_gwp: float
    operational_gwp: float
    total_gwp: float
    intensity_kgco2e_m2: float
    data_quality_summary: Dict[str, int]
    warnings: List[str] = field(default_factory=list)

    def rows_as_dicts(self) -> List[Dict[str, Any]]:
        return [row.to_dict() for row in self.rows]
