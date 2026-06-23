from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .models import EMBODIED_MODULES, MODULES, LineItem, Project, ProjectResult, ResultRow, module_dict


TRANSPORT_FACTORS_KGCO2E_PER_TONNE_KM = {
    "road": 0.1,
    "rail": 0.03,
    "sea": 0.01,
}

MASS_UNITS_TO_KG = {
    "kg": 1.0,
    "kilogram": 1.0,
    "kilograms": 1.0,
    "t": 1000.0,
    "tonne": 1000.0,
    "tonnes": 1000.0,
    "metric ton": 1000.0,
    "metric tons": 1000.0,
    "g": 0.001,
    "gram": 0.001,
    "grams": 0.001,
}

VOLUME_UNITS_TO_M3 = {
    "m3": 1.0,
    "m^3": 1.0,
    "cubic metre": 1.0,
    "cubic meter": 1.0,
    "cubic metres": 1.0,
    "cubic meters": 1.0,
}

AREA_UNITS = {"m2", "m^2", "sqm", "square metre", "square meter", "square metres", "square meters"}
COUNT_UNITS = {"each", "unit", "item", "pcs", "piece", "pieces"}


def normalize_unit(unit: Optional[str]) -> str:
    return (unit or "").strip().lower().replace(" ", " ")


def convert_quantity(
    quantity: float,
    from_unit: str,
    declared_unit: str,
    density_kg_per_m3: Optional[float] = None,
) -> Tuple[Optional[float], List[str]]:
    warnings: List[str] = []
    source = normalize_unit(from_unit)
    target = normalize_unit(declared_unit)

    if quantity is None or quantity <= 0:
        return None, ["Quantity must be greater than zero."]
    if not source or not target:
        return None, ["Both input unit and declared unit are required."]
    if source == target:
        return float(quantity), warnings

    source_is_mass = source in MASS_UNITS_TO_KG
    target_is_mass = target in MASS_UNITS_TO_KG
    source_is_volume = source in VOLUME_UNITS_TO_M3
    target_is_volume = target in VOLUME_UNITS_TO_M3

    if source_is_mass and target_is_mass:
        kg = quantity * MASS_UNITS_TO_KG[source]
        return kg / MASS_UNITS_TO_KG[target], warnings

    if source_is_volume and target_is_volume:
        m3 = quantity * VOLUME_UNITS_TO_M3[source]
        return m3 / VOLUME_UNITS_TO_M3[target], warnings

    if source_is_volume and target_is_mass:
        if not density_kg_per_m3 or density_kg_per_m3 <= 0:
            return None, ["Density is required to convert volume to mass."]
        kg = quantity * VOLUME_UNITS_TO_M3[source] * density_kg_per_m3
        return kg / MASS_UNITS_TO_KG[target], warnings

    if source_is_mass and target_is_volume:
        if not density_kg_per_m3 or density_kg_per_m3 <= 0:
            return None, ["Density is required to convert mass to volume."]
        kg = quantity * MASS_UNITS_TO_KG[source]
        m3 = kg / density_kg_per_m3
        return m3 / VOLUME_UNITS_TO_M3[target], warnings

    if source in AREA_UNITS and target in AREA_UNITS:
        return float(quantity), warnings

    if source in COUNT_UNITS and target in COUNT_UNITS:
        return float(quantity), warnings

    return None, [f"Cannot convert from {from_unit} to {declared_unit} without more data."]


def estimate_mass_kg(item: LineItem, declared_quantity: Optional[float]) -> Tuple[Optional[float], List[str]]:
    warnings: List[str] = []
    source = normalize_unit(item.unit)
    declared = normalize_unit(item.factor.declared_unit)

    if item.quantity and source in MASS_UNITS_TO_KG:
        return item.quantity * MASS_UNITS_TO_KG[source], warnings
    if item.quantity and source in VOLUME_UNITS_TO_M3 and item.density_kg_per_m3:
        return item.quantity * VOLUME_UNITS_TO_M3[source] * item.density_kg_per_m3, warnings
    if declared_quantity and declared in MASS_UNITS_TO_KG:
        return declared_quantity * MASS_UNITS_TO_KG[declared], warnings
    if declared_quantity and declared in VOLUME_UNITS_TO_M3 and item.density_kg_per_m3:
        return declared_quantity * VOLUME_UNITS_TO_M3[declared] * item.density_kg_per_m3, warnings

    warnings.append("A4 transport could not be calculated because mass is unknown.")
    return None, warnings


def calculate_line_item(item: LineItem, project: Project) -> ResultRow:
    warnings: List[str] = []
    module_gwps = module_dict()
    declared_quantity, conversion_warnings = convert_quantity(
        item.quantity,
        item.unit,
        item.factor.declared_unit,
        item.density_kg_per_m3,
    )
    warnings.extend(conversion_warnings)

    mass_kg, mass_warnings = estimate_mass_kg(item, declared_quantity)
    warnings.extend(mass_warnings)

    excluded = declared_quantity is None
    if not excluded:
        module_gwps["A1A3"] = declared_quantity * item.factor.factor("A1A3")
        for module in ("C1", "C2", "C3", "C4"):
            module_gwps[module] = declared_quantity * item.factor.factor(module)

        if mass_kg is not None:
            distance = item.transport_distance_km
            if distance is None:
                distance = project.default_transport_distance_km
            mode = normalize_unit(item.transport_mode) or "road"
            transport_factor = TRANSPORT_FACTORS_KGCO2E_PER_TONNE_KM.get(mode)
            if transport_factor is None:
                warnings.append(f"Unknown transport mode '{item.transport_mode}', road factor used.")
                transport_factor = TRANSPORT_FACTORS_KGCO2E_PER_TONNE_KM["road"]
            module_gwps["A4"] = (mass_kg / 1000.0) * max(distance or 0.0, 0.0) * transport_factor

        wastage_rate = item.wastage_rate if item.wastage_rate is not None else 0.0
        module_gwps["A5"] = module_gwps["A1A3"] * max(wastage_rate, 0.0)

    total = sum(module_gwps.values())
    return ResultRow(
        line_item_id=item.id,
        material_name=item.material_name,
        element_name=item.element_name,
        category=item.category,
        quantity=item.quantity,
        unit=item.unit,
        declared_quantity=declared_quantity or 0.0,
        declared_unit=item.factor.declared_unit,
        mass_kg=mass_kg,
        source_type=item.factor.source_type,
        source=item.factor.source,
        citation=item.factor.citation,
        module_gwps=module_gwps,
        total_gwp=total,
        warnings=warnings,
        excluded=excluded,
    )


def annual_energy_kwh(project: Project) -> float:
    if project.annual_energy_kwh is not None and project.annual_energy_kwh > 0:
        return float(project.annual_energy_kwh)
    if (
        project.energy_intensity_kwh_m2yr is not None
        and project.energy_intensity_kwh_m2yr > 0
        and project.gross_floor_area_m2 > 0
    ):
        return project.energy_intensity_kwh_m2yr * project.gross_floor_area_m2
    return 0.0


def calculate_b6(project: Project) -> Tuple[float, List[str]]:
    warnings: List[str] = []
    energy = annual_energy_kwh(project)
    factor = project.grid_emission_factor_kgco2e_kwh
    if energy > 0 and factor <= 0:
        warnings.append("B6 energy was entered, but grid emission factor is zero or unset.")
    if factor > 0 and energy <= 0:
        warnings.append("Grid emission factor was entered, but annual energy is zero or unset.")
    if factor <= 0:
        warnings.append("B6 defaults to 0 until a sourced grid emission factor is entered.")
    return energy * max(factor, 0.0) * max(project.study_period_years, 0), warnings


def calculate_project(project: Project) -> ProjectResult:
    rows = [calculate_line_item(item, project) for item in project.line_items]
    module_totals = module_dict()
    element_totals: Dict[str, float] = {}
    category_totals: Dict[str, float] = {}
    data_quality_summary: Dict[str, int] = {}
    warnings: List[str] = []

    for row in rows:
        if row.excluded:
            warnings.append(f"{row.material_name} excluded: {'; '.join(row.warnings)}")
            continue
        for module in MODULES:
            module_totals[module] += row.module_gwps.get(module, 0.0)
        element_totals[row.element_name] = element_totals.get(row.element_name, 0.0) + row.total_gwp
        category_totals[row.category] = category_totals.get(row.category, 0.0) + row.total_gwp
        data_quality_summary[row.source_type] = data_quality_summary.get(row.source_type, 0) + 1
        for warning in row.warnings:
            if warning and "A4 transport" not in warning:
                warnings.append(f"{row.material_name}: {warning}")

    b6, b6_warnings = calculate_b6(project)
    module_totals["B6"] = b6
    warnings.extend(b6_warnings)

    embodied = sum(module_totals[module] for module in EMBODIED_MODULES)
    operational = module_totals["B6"]
    total = embodied + operational
    intensity = total / project.gross_floor_area_m2 if project.gross_floor_area_m2 > 0 else 0.0

    return ProjectResult(
        project_id=project.id,
        project_name=project.name,
        rows=rows,
        module_totals=module_totals,
        element_totals=element_totals,
        category_totals=category_totals,
        embodied_gwp=embodied,
        operational_gwp=operational,
        total_gwp=total,
        intensity_kgco2e_m2=intensity,
        data_quality_summary=data_quality_summary,
        warnings=warnings,
    )
