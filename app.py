from __future__ import annotations

import io
from copy import deepcopy
from typing import Dict, List

import pandas as pd
import plotly.express as px
import streamlit as st

from lca.engine import TRANSPORT_FACTORS_KGCO2E_PER_TONNE_KM, calculate_project
from lca.factors.generic import GenericFactorAdapter
from lca.factors.okobaudat import OkobaudatAdapter
from lca.factors.openlca import OpenLCAIPCClient, discover_openlca, ipc_command
from lca.models import MODULES, EmissionFactorSet, LineItem, Project, module_dict, new_id
from lca.persistence import list_project_files, load_project, save_project


st.set_page_config(page_title="LCA Carbon Calculator", layout="wide")

ELEMENT_CATEGORIES = [
    "Substructure",
    "Superstructure / frame",
    "Envelope",
    "Internal finishes",
    "Services",
    "Other",
]


@st.cache_resource
def generic_adapter() -> GenericFactorAdapter:
    return GenericFactorAdapter()


@st.cache_resource
def okobaudat_adapter() -> OkobaudatAdapter:
    return OkobaudatAdapter()


def blank_option(name: str) -> Project:
    adapter = generic_adapter()
    factor = adapter.get("generic-concrete-c30")
    defaults = adapter.defaults_for("generic-concrete-c30")
    return Project(
        name=name,
        building_type="Office",
        gross_floor_area_m2=1000,
        study_period_years=60,
        location="Unspecified",
        energy_intensity_kwh_m2yr=0.0,
        grid_emission_factor_kgco2e_kwh=0.0,
        line_items=[
            LineItem(
                element_name="Frame",
                category="Superstructure / frame",
                material_name=factor.material_name,
                quantity=100000,
                unit="kg",
                density_kg_per_m3=defaults["density_kg_per_m3"],
                transport_distance_km=50,
                transport_mode="road",
                wastage_rate=defaults["wastage_rate"],
                factor=factor,
                notes="Starter example. Replace with project quantities.",
            )
        ],
    )


def init_state() -> None:
    if "projects" not in st.session_state:
        st.session_state.projects = {"Option A": blank_option("Option A")}
    if "current_project_name" not in st.session_state:
        st.session_state.current_project_name = "Option A"


def current_project() -> Project:
    return st.session_state.projects[st.session_state.current_project_name]


def set_current_project(project: Project) -> None:
    old_name = st.session_state.current_project_name
    if old_name != project.name:
        st.session_state.projects.pop(old_name, None)
        st.session_state.current_project_name = project.name
    st.session_state.projects[project.name] = project


def line_items_to_frame(items: List[LineItem]) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    for item in items:
        row = {
            "id": item.id,
            "element_name": item.element_name,
            "category": item.category,
            "material_name": item.material_name,
            "quantity": item.quantity,
            "unit": item.unit,
            "declared_unit": item.factor.declared_unit,
            "density_kg_per_m3": item.density_kg_per_m3,
            "transport_distance_km": item.transport_distance_km,
            "transport_mode": item.transport_mode,
            "wastage_rate": item.wastage_rate,
            "source_type": item.factor.source_type,
            "source": item.factor.source,
            "A1A3": item.factor.factor("A1A3"),
            "C1": item.factor.factor("C1"),
            "C2": item.factor.factor("C2"),
            "C3": item.factor.factor("C3"),
            "C4": item.factor.factor("C4"),
            "citation": item.factor.citation,
            "notes": item.notes,
        }
        rows.append(row)
    return pd.DataFrame(rows)


def frame_to_line_items(frame: pd.DataFrame) -> List[LineItem]:
    items: List[LineItem] = []
    for _, row in frame.fillna("").iterrows():
        material = str(row.get("material_name", "")).strip()
        if not material:
            continue
        factors = module_dict()
        for module in ("A1A3", "C1", "C2", "C3", "C4"):
            factors[module] = as_float(row.get(module, 0.0))
        factor = EmissionFactorSet(
            record_id=str(row.get("id", "")) or new_id("factor"),
            material_name=material,
            source=str(row.get("source", "")) or "manual",
            source_type=str(row.get("source_type", "")) or "override",
            declared_unit=str(row.get("declared_unit", "")) or str(row.get("unit", "kg")),
            gwp_by_module=factors,
            citation=str(row.get("citation", "")),
            data_quality=str(row.get("source_type", "")) or "manual",
        )
        items.append(
            LineItem(
                id=str(row.get("id", "")) or new_id("line"),
                element_name=str(row.get("element_name", "")) or "Unassigned",
                category=str(row.get("category", "")) or "Other",
                material_name=material,
                quantity=as_float(row.get("quantity", 0.0)),
                unit=str(row.get("unit", "")) or "kg",
                density_kg_per_m3=as_optional_float(row.get("density_kg_per_m3")),
                transport_distance_km=as_optional_float(row.get("transport_distance_km")),
                transport_mode=str(row.get("transport_mode", "")) or "road",
                wastage_rate=as_optional_float(row.get("wastage_rate")),
                factor=factor,
                notes=str(row.get("notes", "")),
            )
        )
    return items


def as_float(value: object, default: float = 0.0) -> float:
    try:
        if value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def as_optional_float(value: object):
    if value in ("", None):
        return None
    return as_float(value)


def result_to_csv(result) -> bytes:
    frame = pd.DataFrame(result.rows_as_dicts())
    columns = [
        "material_name",
        "element_name",
        "category",
        "quantity",
        "unit",
        "declared_quantity",
        "declared_unit",
        "mass_kg",
        "source_type",
        "source",
        "citation",
    ] + list(MODULES) + ["total_gwp", "warnings", "excluded"]
    available = [column for column in columns if column in frame.columns]
    return frame[available].to_csv(index=False).encode("utf-8")


def result_to_html(project: Project, result) -> bytes:
    rows = "".join(
        f"<tr><td>{module}</td><td>{value:,.1f}</td></tr>"
        for module, value in result.module_totals.items()
    )
    html = f"""
    <html>
      <head>
        <title>{project.name} LCA Summary</title>
        <style>
          body {{ font-family: Arial, sans-serif; margin: 2rem; color: #1f2933; }}
          table {{ border-collapse: collapse; width: 100%; margin-top: 1rem; }}
          th, td {{ border: 1px solid #d9e2ec; padding: 0.5rem; text-align: left; }}
          th {{ background: #f0f4f8; }}
          .muted {{ color: #52606d; }}
        </style>
      </head>
      <body>
        <h1>{project.name}</h1>
        <p class="muted">Screening LCA summary aligned to EN 15978 module structure.</p>
        <p><strong>Total:</strong> {result.total_gwp:,.1f} kg CO2e</p>
        <p><strong>Intensity:</strong> {result.intensity_kgco2e_m2:,.1f} kg CO2e/m2</p>
        <h2>Module Totals</h2>
        <table><tr><th>Module</th><th>kg CO2e</th></tr>{rows}</table>
        <h2>Data Quality</h2>
        <p>{result.data_quality_summary}</p>
        <p class="muted">Generic seed factors are for screening and app testing only. Replace with EPD/openLCA data before external reporting.</p>
      </body>
    </html>
    """
    return html.encode("utf-8")


def sidebar() -> None:
    st.sidebar.title("Project Options")
    names = list(st.session_state.projects.keys())
    selected = st.sidebar.selectbox(
        "Current option",
        names,
        index=names.index(st.session_state.current_project_name),
    )
    st.session_state.current_project_name = selected

    if st.sidebar.button("Duplicate option"):
        source = current_project()
        copy = deepcopy(source)
        copy.id = new_id("project")
        copy.name = f"{source.name} copy"
        for item in copy.line_items:
            item.id = new_id("line")
        st.session_state.projects[copy.name] = copy
        st.session_state.current_project_name = copy.name
        st.rerun()

    project_files = list_project_files()
    if project_files:
        labels = [path.name for path in project_files]
        chosen = st.sidebar.selectbox("Load saved project", [""] + labels)
        if chosen and st.sidebar.button("Load"):
            path = next(path for path in project_files if path.name == chosen)
            loaded = load_project(path)
            st.session_state.projects[loaded.name] = loaded
            st.session_state.current_project_name = loaded.name
            st.rerun()


def render_setup(project: Project) -> Project:
    st.subheader("Project setup")
    col1, col2, col3 = st.columns(3)
    with col1:
        project.name = st.text_input("Project / option name", project.name)
        project.building_type = st.text_input("Building type", project.building_type)
        project.location = st.text_input("Location", project.location)
    with col2:
        project.gross_floor_area_m2 = st.number_input(
            "Gross floor area (m2)",
            min_value=0.0,
            value=float(project.gross_floor_area_m2),
            step=100.0,
        )
        project.study_period_years = int(
            st.number_input("Study period (years)", min_value=1, value=int(project.study_period_years), step=1)
        )
        project.default_transport_distance_km = st.number_input(
            "Default A4 distance (km)",
            min_value=0.0,
            value=float(project.default_transport_distance_km),
            step=10.0,
        )
    with col3:
        project.energy_intensity_kwh_m2yr = st.number_input(
            "B6 energy intensity (kWh/m2/yr)",
            min_value=0.0,
            value=float(project.energy_intensity_kwh_m2yr or 0.0),
            step=5.0,
        )
        project.annual_energy_kwh = st.number_input(
            "B6 annual energy override (kWh/yr)",
            min_value=0.0,
            value=float(project.annual_energy_kwh or 0.0),
            step=1000.0,
        )
        if project.annual_energy_kwh == 0:
            project.annual_energy_kwh = None
        project.grid_emission_factor_kgco2e_kwh = st.number_input(
            "Grid factor (kgCO2e/kWh)",
            min_value=0.0,
            value=float(project.grid_emission_factor_kgco2e_kwh or 0.0),
            step=0.01,
            format="%.4f",
        )
        project.grid_factor_source = st.text_input("Grid factor source", project.grid_factor_source)
    return project


def render_inventory(project: Project) -> Project:
    st.subheader("Inventory")
    st.caption("Use generic seed factors to start, or type user-supplied factors directly in the table.")

    adapter = generic_adapter()
    with st.expander("Add from bundled generic factors", expanded=True):
        query = st.text_input("Search material", "")
        candidates = adapter.search(query, limit=20)
        labels = [
            f"{candidate.material_name} | {candidate.preview_gwp_a1a3:g} kgCO2e/{candidate.declared_unit}"
            for candidate in candidates
        ]
        if labels:
            selected = st.selectbox("Candidate", labels)
            selected_index = labels.index(selected)
            candidate = candidates[selected_index]
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                element_name = st.text_input("Element name", "Frame")
            with col2:
                category = st.selectbox("Category", ELEMENT_CATEGORIES)
            with col3:
                quantity = st.number_input("Quantity", min_value=0.0, value=1000.0, step=100.0)
            with col4:
                unit = st.text_input("Input unit", candidate.declared_unit)
            if st.button("Add material"):
                factor = adapter.get(candidate.record_id)
                defaults = adapter.defaults_for(candidate.record_id)
                project.line_items.append(
                    LineItem(
                        element_name=element_name,
                        category=category,
                        material_name=factor.material_name,
                        quantity=quantity,
                        unit=unit,
                        density_kg_per_m3=defaults["density_kg_per_m3"],
                        transport_distance_km=project.default_transport_distance_km,
                        transport_mode="road",
                        wastage_rate=defaults["wastage_rate"],
                        factor=factor,
                    )
                )
                st.rerun()
        else:
            st.info("No generic factor matched that search.")

    with st.expander("Add from ÖKOBAUDAT (live EPD database)", expanded=False):
        st.caption(
            "Searches the German Federal ÖKOBAUDAT database via its public soda4LCA API "
            "(no key required; needs internet). Imports third-party EPD data: A1–A3 and C1–C4 "
            "modules. A4/A5/B6 stay engine-derived to avoid double counting."
        )
        oko = okobaudat_adapter()
        col_q, col_n = st.columns([3, 1])
        with col_q:
            oko_query = st.text_input("Search EPD materials", "concrete", key="oko_query")
        with col_n:
            oko_n = st.number_input("Max results", min_value=1, max_value=50, value=15, step=5, key="oko_n")
        if st.button("Search ÖKOBAUDAT"):
            try:
                with st.spinner("Querying ÖKOBAUDAT…"):
                    st.session_state["oko_candidates"] = [c.__dict__ for c in oko.search(oko_query, limit=int(oko_n))]
                    st.session_state["oko_total"] = oko.total_count(oko_query)
            except Exception as exc:  # network/parse failure must never block the app
                st.session_state["oko_candidates"] = []
                st.error(f"ÖKOBAUDAT request failed: {exc}. Generic and manual factors still work.")
        candidates = st.session_state.get("oko_candidates", [])
        if candidates:
            st.caption(f"{st.session_state.get('oko_total', len(candidates))} total matches; showing {len(candidates)}.")
            labels = [f"{c['material_name'][:70]} | {c['geography']}" for c in candidates]
            chosen = st.selectbox("EPD record", labels, key="oko_choice")
            chosen_c = candidates[labels.index(chosen)]
            c1, c2, c3 = st.columns(3)
            with c1:
                oko_element = st.text_input("Element name", "Frame", key="oko_el")
            with c2:
                oko_category = st.selectbox("Category", ELEMENT_CATEGORIES, key="oko_cat")
            with c3:
                oko_qty = st.number_input("Quantity", min_value=0.0, value=10.0, step=1.0, key="oko_qty")
            if st.button("Add EPD material"):
                try:
                    with st.spinner("Loading EPD dataset…"):
                        factor = oko.get(chosen_c["record_id"])
                    project.line_items.append(
                        LineItem(
                            element_name=oko_element,
                            category=oko_category,
                            material_name=factor.material_name,
                            quantity=oko_qty,
                            unit=factor.declared_unit,
                            density_kg_per_m3=factor.__dict__.get("density_kg_per_m3_hint"),
                            transport_distance_km=project.default_transport_distance_km,
                            transport_mode="road",
                            wastage_rate=0.0,
                            factor=factor,
                            notes="ÖKOBAUDAT EPD. Set wastage/density to enable A5/A4 if needed.",
                        )
                    )
                    st.success(
                        f"Added {factor.material_name[:50]} "
                        f"({factor.declared_unit}, A1–A3 {factor.gwp_by_module['A1A3']:.3g} kgCO2e)."
                    )
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not load EPD dataset: {exc}")

    frame = line_items_to_frame(project.line_items)
    edited = st.data_editor(
        frame,
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True,
        column_config={
            "id": st.column_config.TextColumn("id", disabled=True),
            "category": st.column_config.SelectboxColumn("category", options=ELEMENT_CATEGORIES),
            "transport_mode": st.column_config.SelectboxColumn(
                "transport_mode", options=list(TRANSPORT_FACTORS_KGCO2E_PER_TONNE_KM.keys())
            ),
            "source_type": st.column_config.SelectboxColumn("source_type", options=["generic", "epd", "override", "openlca"]),
        },
    )
    project.line_items = frame_to_line_items(edited)
    return project


def render_results(project: Project):
    st.subheader("Results")
    result = calculate_project(project)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total GWP", f"{result.total_gwp:,.0f} kg CO2e")
    col2.metric("Intensity", f"{result.intensity_kgco2e_m2:,.1f} kg CO2e/m2")
    col3.metric("Embodied", f"{result.embodied_gwp:,.0f} kg CO2e")
    col4.metric("Operational B6", f"{result.operational_gwp:,.0f} kg CO2e")

    if result.warnings:
        with st.expander("Warnings and assumptions", expanded=True):
            for warning in result.warnings:
                st.warning(warning)

    module_frame = pd.DataFrame(
        [{"module": module, "kgCO2e": value} for module, value in result.module_totals.items()]
    )
    element_frame = pd.DataFrame(
        [{"element": element, "kgCO2e": value} for element, value in result.element_totals.items()]
    )
    left, right = st.columns(2)
    with left:
        st.plotly_chart(px.bar(module_frame, x="module", y="kgCO2e", title="Breakdown by EN 15978 module"), use_container_width=True)
    with right:
        if not element_frame.empty:
            st.plotly_chart(px.bar(element_frame, x="element", y="kgCO2e", title="Breakdown by element"), use_container_width=True)

    st.write("Data quality", result.data_quality_summary)
    st.dataframe(pd.DataFrame(result.rows_as_dicts()), use_container_width=True)
    return result


def render_compare() -> None:
    st.subheader("Compare options")
    names = list(st.session_state.projects.keys())
    if len(names) < 2:
        st.info("Duplicate an option from the sidebar to compare designs.")
        return
    left_name, right_name = st.columns(2)
    with left_name:
        option_a = st.selectbox("Option A", names, index=0)
    with right_name:
        option_b = st.selectbox("Option B", names, index=1)
    result_a = calculate_project(st.session_state.projects[option_a])
    result_b = calculate_project(st.session_state.projects[option_b])
    delta = result_b.total_gwp - result_a.total_gwp
    pct = (delta / result_a.total_gwp * 100.0) if result_a.total_gwp else 0.0
    st.metric("Delta, B minus A", f"{delta:,.0f} kg CO2e", f"{pct:,.1f}%")

    rows = []
    for module in MODULES:
        rows.append(
            {
                "module": module,
                option_a: result_a.module_totals[module],
                option_b: result_b.module_totals[module],
                "delta": result_b.module_totals[module] - result_a.module_totals[module],
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True)


def render_export(project: Project, result) -> None:
    st.subheader("Export and save")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button("Download line-item CSV", result_to_csv(result), file_name=f"{project.name}-lca-results.csv")
    with col2:
        st.download_button("Download HTML summary", result_to_html(project, result), file_name=f"{project.name}-lca-summary.html")
    with col3:
        if st.button("Save project JSON"):
            path = save_project(project)
            st.success(f"Saved to {path}")


def render_openlca() -> None:
    st.subheader("openLCA connection")
    st.caption(
        "Local-only power feature: connects to openLCA running on your own machine. "
        "On a hosted deployment (e.g. Streamlit Cloud) this will report 'not found' — "
        "that is expected. Use ÖKOBAUDAT (Inventory tab) for the live, hosted data source."
    )
    status = discover_openlca()
    col1, col2, col3 = st.columns(3)
    col1.metric("App found", "yes" if status.app_found else "no")
    col2.metric("Workspace found", "yes" if status.workspace_found else "no")
    col3.metric("Databases detected", len(status.database_names))
    st.code(status.app_path)
    st.code(status.workspace_path)
    if status.database_names:
        db_name = st.selectbox("Database", status.database_names)
        st.write("IPC command")
        st.code(" ".join(ipc_command(db_name)))
        client = OpenLCAIPCClient()
        if st.button("Check running IPC server"):
            if client.is_available():
                st.success("openLCA IPC server responded.")
            else:
                st.warning("No running IPC server responded on http://127.0.0.1:8080.")
    else:
        st.info("No openLCA database folder was detected in ~/openLCA-data-1.4. Import or create a database in openLCA, then this app can connect through the bundled IPC server.")


def main() -> None:
    init_state()
    sidebar()
    st.title("LCA Carbon Calculator")
    st.caption("Early-stage whole-life carbon screening by EN 15978 modules.")

    project = current_project()
    setup_tab, inventory_tab, results_tab, compare_tab, export_tab, openlca_tab = st.tabs(
        ["Setup", "Inventory", "Results", "Compare", "Export", "openLCA"]
    )
    with setup_tab:
        project = render_setup(project)
    with inventory_tab:
        project = render_inventory(project)
    set_current_project(project)
    with results_tab:
        result = render_results(project)
    with compare_tab:
        render_compare()
    with export_tab:
        render_export(project, calculate_project(project))
    with openlca_tab:
        render_openlca()


if __name__ == "__main__":
    main()
