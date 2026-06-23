# Product Requirements Document — LCA Carbon Calculator (EN 15978)

| | |
|---|---|
| **Product** | LCA Carbon Calculator — early-stage embodied & operational carbon assessment |
| **Standard alignment** | EN 15978 (building-level assessment) · EN 15804 (product EPDs) · ISO 14040 / 14044 (LCA framework) |
| **Platform** | Python · Streamlit web app |
| **Document type** | Technical build specification (PRD) |
| **Version** | 0.1 (draft) |
| **Date** | 23 June 2026 |
| **Author** | Upasana Sen |
| **Status** | Draft for review |

> **Scope note on standards:** EN 15978 and EN 15804 are copyrighted standards published by CEN; their full normative text is paywalled. This PRD describes the widely-documented lifecycle-module framework defined by those standards, not verbatim normative clauses. Before publishing carbon results externally, the methodology should be checked against a licensed copy of EN 15978:2011 and the relevant national annex.

---

## 1. TL;DR

The LCA Carbon Calculator is a Streamlit web application that lets architects, engineers, and sustainability consultants estimate the **whole-life carbon** of a building **at the early design stage**, when a model is still a rough bill of quantities rather than a detailed BIM file. The user enters building elements and material quantities, the app pulls third-party-verified emission factors from public **Environmental Product Declaration (EPD)** databases, and it returns global warming potential (GWP, in kg CO₂e) broken down by **EN 15978 lifecycle module** (A1–A5, B6, C1–C4) and by building element.

The differentiator is **transparency and standard-alignment**: every number is traceable to a named data source and a named lifecycle module, and the methodology follows the ISO 14040/44 LCA framework. The target outcome is to let a design team compare two structural or material options on carbon in minutes, not weeks.

---

## 2. Problem statement

Embodied carbon — the emissions locked into materials and construction before a building is even occupied — is decided early in design but measured late, if at all. Whole-building LCA today is typically performed by specialist consultants near the end of design development, using desktop tools that require a near-complete BIM model. By then the high-leverage decisions (structural system, primary materials, massing) are frozen, so the assessment documents the carbon rather than reducing it.

The people making those early decisions — architects and engineers in concept and schematic design — rarely have a fast, credible way to test "what if we used X instead of Y?" against a recognised standard. The cost of not solving this is locked-in embodied carbon that cannot be undone, weaker competitive positioning as procurement increasingly asks for carbon data, and reliance on expensive late-stage consulting.

---

## 3. Background: the standards (primer)

This section is build context, not requirements. It defines the vocabulary the rest of the spec uses.

**ISO 14040 / ISO 14044** define the general framework for Life Cycle Assessment: goal & scope definition, inventory analysis, impact assessment, and interpretation. They are method-agnostic and apply to any product. Our calculator implements a *cradle-to-grave* (with optional cradle-to-gate) assessment consistent with this framework.

**EN 15804** is the European standard governing **product-level EPDs** for construction products. EPDs declare environmental impacts (including GWP) per a defined functional/declared unit (e.g. per kg, per m³, per m²). EPDs are the emission-factor data source for this tool.

**EN 15978** is the European standard for assessing the environmental performance of a **whole building**. It organises a building's life cycle into information modules:

| Module | Stage | Description |
|---|---|---|
| **A1** | Product | Raw material supply |
| **A2** | Product | Transport (to manufacturer) |
| **A3** | Product | Manufacturing |
| **A4** | Construction | Transport to site |
| **A5** | Construction | Construction / installation (incl. material wastage) |
| B1 | Use | Material use / emissions in use |
| B2 | Use | Maintenance |
| B3 | Use | Repair |
| B4 | Use | Replacement |
| B5 | Use | Refurbishment |
| **B6** | Use | Operational energy use |
| B7 | Use | Operational water use |
| **C1** | End of life | Deconstruction / demolition |
| **C2** | End of life | Transport (to waste processing) |
| **C3** | End of life | Waste processing |
| **C4** | End of life | Disposal |
| D | Beyond boundary | Reuse / recovery / recycling benefits & loads |

**A1–A3** are almost always reported together (the "cradle-to-gate" product stage) because EPDs declare them as a bundle.

**Modules in scope for this product (bolded above): A1–A3, A4, A5, B6, C1–C4.** Modules B1–B5, B7, and D are out of MVP scope (see Non-Goals).

---

## 4. Goals

1. **Enable a credible early-stage carbon comparison.** A user can model two design options and see the GWP delta by module and element in a single session (target: full comparison in < 15 minutes for a 20-line bill of quantities).
2. **Make every result traceable.** 100% of reported GWP values link back to a named data source (EPD or database record) and a named EN 15978 module — no "black box" totals.
3. **Cover whole-life carbon, not just embodied.** Report embodied (A, C) *and* operational energy (B6) so totals reflect the dominant lifecycle drivers for the chosen study period.
4. **Reduce dependence on specialist tooling for screening.** Give non-specialists a defensible first-pass number without a full BIM model or a consultant.
5. **Produce a shareable, standard-aligned output.** Export a results summary (CSV + PDF/HTML) structured by EN 15978 module suitable for a design review.

---

## 5. Non-goals

1. **Not a certified/compliance LCA tool (v1).** Output is a screening estimate for decision support, not a verified EN 15978 assessment for green-building certification (e.g. LEED, BREEAM) or regulatory filing. *Why: verification and audited datasets are a large separate effort; early-design screening delivers most of the value first.*
2. **No modules B1–B5, B7, or D in v1.** Maintenance, replacement, refurbishment, operational water, and end-of-life recovery credits are excluded. *Why: they require service-life and scenario data rarely available at concept stage; A/B6/C capture the largest share of whole-life carbon for most buildings.*
3. **No BIM/IFC import in v1.** Input is manual or CSV upload, not a parsed Revit/IFC model. *Why: robust BIM parsing is its own engineering track; the early-design user often has no model yet.*
4. **Not a cost estimator.** Carbon only, no $ / embodied-cost coupling. *Why: keeps the data model and scope focused.*
5. **No multi-user accounts / collaboration in v1.** Single-session, single-user. *Why: avoids backend/auth complexity until the calculation core is proven.*

---

## 6. Target users & personas

| Persona | Role | Need | Sophistication |
|---|---|---|---|
| **Asha — Design architect** | Concept/schematic architect | Quick "which option is greener" answers during design | Low LCA knowledge; high design context |
| **Ravi — Structural / sustainability engineer** | Engineer or in-house sustainability lead | Defensible early numbers, module-level breakdown, sensitivity to material choice | Medium-high; understands EPDs and modules |
| **Maya — Sustainability consultant** | External consultant doing rapid screening before a full LCA | Fast triage, traceable sources, exportable summary | High; will scrutinise data provenance |

Primary persona for v1: **Ravi** (enough domain literacy to value module-level transparency, enough volume of decisions to need speed). Asha drives the UX simplicity bar; Maya drives the traceability bar.

---

## 7. User stories

Grouped by persona, ordered by priority within group.

**Project setup**
- As an engineer, I want to create a project with a name, gross floor area, study period (years), and location so that operational and transport calculations have the right basis.
- As an architect, I want to start from a template (e.g. "concrete frame office") so that I am not facing a blank sheet.

**Inventory entry**
- As an engineer, I want to add building elements (e.g. substructure, frame, façade) and assign materials with quantities so that the model mirrors how I think about the building.
- As a user, I want to upload a bill of quantities as CSV so that I do not retype an existing take-off.
- As a user, I want to enter a quantity in a unit I have (kg, m³, m²) and have the app reconcile it with the EPD's declared unit so that I am not doing manual unit math.

**Emission factors**
- As a consultant, I want to search a connected EPD database for a material and pick a specific EPD so that my factor is traceable to a real declaration.
- As an engineer, I want a sensible generic/default factor when no specific EPD is selected so that I can still get a first number, clearly flagged as generic.
- As a user, I want to override any factor manually and record a note/source so that I can use a value from a supplier datasheet.

**Calculation & results**
- As an engineer, I want GWP broken down by EN 15978 module and by element so that I can see where the carbon is.
- As an architect, I want to duplicate a project as "Option B", change a few materials, and see the delta so that I can compare designs.
- As a user, I want to see which inputs are generic vs. EPD-specific so that I know how much to trust the total.

**Export**
- As a consultant, I want to export results as CSV and a formatted report so that I can drop them into a design review.

**Edge / error cases**
- As a user, when an EPD database is unreachable, I want the app to fall back to cached/generic factors and tell me clearly so that I am not blocked.
- As a user, when a quantity or unit is missing/invalid, I want an inline validation error so that totals are never silently wrong.

---

## 8. Functional requirements

Prioritised **P0 (must-have / MVP)**, **P1 (fast follow)**, **P2 (future, design for it)**.

### 8.1 Project & inventory management

**P0**
- Create / edit / delete a project with: name, building type, gross floor area (m²), study period (years, default 60), location (country/region for energy grid + transport defaults).
- Add elements grouped by a standard element taxonomy (substructure, superstructure/frame, envelope, internal finishes, services — a simplified Uniclass/RICS-style grouping).
- Add line items: material, quantity, unit (kg / m³ / m² / each), optional density (to convert volume↔mass), optional transport distance (A4), optional wastage factor (A5).
- Duplicate a project to create design options for comparison.

*Acceptance criteria*
- [ ] Given a project with ≥1 valid line item, when the user requests results, then a total GWP and per-module breakdown are produced.
- [ ] Given a line item in m³ and an EPD declared per kg, when a density is provided, then the app converts correctly and shows the converted mass.
- [ ] Given a missing required field (quantity or unit), then the line item is flagged and excluded from totals with a visible warning.

**P1**
- CSV bill-of-quantities upload with column mapping.
- Project templates (pre-filled archetypes).

**P2**
- IFC/BIM quantity import.
- Element-level service life for B4 replacement modelling.

### 8.2 Emission-factor data (EPD integration)

**P0**
- Integrate at least one open EPD data source (see §11). Search by material name; display candidate EPDs with: declared unit, GWP A1–A3, geography, validity date, source.
- Allow selection of a specific EPD record; persist the chosen record's identifier with the line item.
- Provide a bundled set of **generic/default factors** for common materials so the app works offline / before a database pick, clearly labelled "generic".
- Manual factor override with a free-text source note.

*Acceptance criteria*
- [ ] Given a material search, when the database returns results, then each result shows GWP value, unit, and a source attribution.
- [ ] Given an EPD is selected, when results are computed, then the line item's factor, unit, and source match the selected EPD.
- [ ] Given the database is unavailable, then the app uses cached/generic factors and shows a non-blocking "using generic data" notice.
- [ ] Given a manual override, then the override value and note are used and visibly marked as user-supplied.

**P1**
- Cache EPD lookups locally to reduce API calls and enable offline reuse.
- Multiple data sources with source preference order and de-duplication.

**P2**
- Background refresh of cached EPDs on validity expiry; alert on expired EPDs.

### 8.3 Calculation engine

**P0** — Compute GWP per module per line item, aggregate to element and project level. Modules in scope: A1–A3, A4, A5, B6, C1–C4. See §10 for the methodology and formulas.

*Acceptance criteria*
- [ ] Module math matches the formulas in §10 for a documented worked example (unit-tested).
- [ ] Changing a quantity, factor, distance, or wastage value updates totals deterministically.
- [ ] Totals are reproducible: identical inputs always yield identical outputs (no hidden randomness; pinned factor data).

**P1** — Sensitivity view: show contribution % by element/material; highlight top carbon drivers.

**P2** — Uncertainty ranges (e.g. low/expected/high factor bands); Monte Carlo on factor uncertainty.

### 8.4 Results, comparison & export

**P0**
- Results dashboard: total GWP (kg CO₂e and kg CO₂e/m²), breakdown by module (stacked bar), breakdown by element (bar/table), embodied vs operational split.
- Side-by-side comparison of two projects/options with absolute and % delta.
- Export results to CSV; export a formatted summary (HTML or PDF) structured by module.

*Acceptance criteria*
- [ ] Given results exist, then the dashboard shows module and element breakdowns whose parts sum to the displayed total (within rounding).
- [ ] Given two options, then comparison shows per-module deltas and an overall delta.
- [ ] Given an export request, then the CSV contains every line item with material, quantity, unit, factor, source, module GWPs, and totals.

**P1** — Save/load projects to disk (JSON); shareable export bundle.

**P2** — Benchmark against published GWP/m² ranges by building type (requires a vetted benchmark dataset — flagged as needing a real source).

---

## 9. Non-functional requirements

- **Transparency:** every displayed figure must be drillable to its inputs (quantity × factor, with module and source). This is a product principle, not a nice-to-have.
- **Reproducibility:** factor datasets are versioned/pinned; a result records which dataset version produced it.
- **Performance:** recalculation of a ≤200-line project in < 1 s after an input change; EPD search response surfaced in < 3 s (network-dependent; show a spinner and allow generic fallback).
- **Resilience:** no external dependency may be a single point of failure for producing *a* number — generic factors always allow a fallback estimate.
- **Accuracy honesty:** the UI must distinguish EPD-specific vs generic vs user-override factors, and must never present a generic-data estimate as if it were EPD-verified.
- **Portability:** runs locally with `streamlit run` and deploys to Streamlit Community Cloud with no paid infra.

---

## 10. Calculation methodology

All impacts are **Global Warming Potential (GWP100)** in **kg CO₂e**. The general LCA relationship per line item is:

```
module_GWP = quantity_in_declared_unit × emission_factor_for_module
```

Quantities are normalised to the EPD's declared unit before multiplication (mass↔volume via density; area via thickness/areal density where needed).

### A1–A3 — Product stage (cradle-to-gate)
```
GWP_A1A3 = mass_or_declared_qty × factor_A1A3
```
`factor_A1A3` comes directly from the selected EPD (or generic default). This is the core embodied figure.

### A4 — Transport to site
```
GWP_A4 = mass_tonnes × distance_km × transport_emission_factor (kgCO2e per tonne-km)
```
Transport factor depends on mode (road/rail/sea). Provide editable defaults by mode; default distance configurable per project.

### A5 — Construction / installation (incl. wastage)
Two components:
```
GWP_A5_waste = GWP_A1A3 × wastage_rate            # embodied carbon of wasted material
GWP_A5_site  = (site energy / process factor)      # optional, often small at early stage
```
MVP models wastage (material-specific default rate, editable). Site-process energy is optional/editable, default 0 with a note.

### B6 — Operational energy use
```
GWP_B6 = annual_energy_use (kWh/yr) × grid_emission_factor (kgCO2e/kWh) × study_period_years
```
`annual_energy_use` is entered directly or estimated from floor area × an editable energy-intensity (kWh/m²/yr). `grid_emission_factor` defaults by location and is editable. **Grid factors fall over time and vary by country — these defaults must be sourced from an official dataset and dated (flagged; do not hard-code unsourced values).**

### C1–C4 — End of life
```
GWP_C = mass_or_declared_qty × factor_C(module)
```
End-of-life factors (per module C1–C4) come from the EPD where declared; otherwise generic scenario factors by material/disposal route. Where an EPD reports C as a combined value, store it against C and note the aggregation.

### Aggregation
```
embodied_GWP    = Σ (A1A3 + A4 + A5 + C1..C4) over all line items
operational_GWP = Σ B6
total_GWP       = embodied_GWP + operational_GWP
intensity       = total_GWP / gross_floor_area      # kgCO2e/m²
```

### Worked example (illustrative factors — NOT real data)
> The numbers below are placeholders to validate the math, not sourced emission factors. Replace with EPD/database values before any real use.

- 100,000 kg of a material; `factor_A1A3 = 0.12 kgCO2e/kg` (illustrative) → **A1–A3 = 12,000 kg CO₂e**
- Transport 50 km at `0.0001 kgCO2e/(kg·km)` (illustrative) → A4 = 100,000 × 50 × 0.0001 = **500 kg CO₂e**
- Wastage 5% → A5 = 12,000 × 0.05 = **600 kg CO₂e**
- End of life `factor_C = 0.02 kgCO2e/kg` (illustrative) → C = **2,000 kg CO₂e**
- Embodied for this item = 12,000 + 500 + 600 + 2,000 = **15,100 kg CO₂e**

Each step must be covered by a unit test using these documented inputs.

---

## 11. EPD data source integration

The "comprehensive" data strategy is to read emission factors from external, third-party-verified EPD databases via API, with a bundled generic dataset as a guaranteed fallback. Two complementary public sources are recommended for v1.

> **Verify before building:** API endpoints, authentication, and access terms below were confirmed from public documentation as of mid-2025 and are changing (notably EC3's "2.0" modernization of its API program). Re-check the live developer docs and terms of use before integrating, and confirm attribution requirements.

### 11.1 EC3 / openEPD (Building Transparency)
- **What:** the largest open-access database of digital, third-party-verified EPDs; GWP reported in kg CO₂e.
- **Access model:** requires an EC3 account and an API key (created in EC3 Key Management). **Free** API access for individuals affiliated with a verified organization/institution; **paid** tier required for production use. Building Transparency asks to be notified before integrating EC3 data, and **attribution to Building Transparency/EC3 is required**.
- **Endpoints (verify):** openEPD API base `https://openepd.buildingtransparency.org/api`; an EC3 materials endpoint historically at `https://etl-api.cqd.io/api/materials`. Querying uses an "Open Material Filter" (OMF) query language; responses can be filtered to return fields such as `gwp`.
- **Why for us:** breadth, global coverage, active ecosystem (Autodesk, cove.tool, etc. integrate it), strong provenance — satisfies Maya's traceability bar.

### 11.2 ÖKOBAUDAT (German Federal Ministry, via soda4LCA)
- **What:** government-maintained LCA/EPD database; ~1,400+ datasets in German and English; GWP in kg CO₂e with explicit reference units (kg, m³, pcs, MJ). Data is **publicly available free of charge**.
- **Access model:** RESTful **soda4LCA** service interface. Data is in the EC-derived **ILCD** format (extended for EN 15804). Return format defaults to XML; pass `format=JSON` for JSON. An "extended view" returns all referenced secondary data inline in one request.
- **Why for us:** fully open, no auth gate, stable government stewardship — ideal default source and a clean fallback when EC3 access is constrained.

### 11.3 Integration design
- A **data-source adapter layer** with a common internal interface: `search(material_query) -> [FactorCandidate]` and `get(record_id) -> EmissionFactorSet`. Each source (EC3, Ökobaudat, bundled-generic) implements the adapter, normalising to our internal `EmissionFactorSet` (per-module GWP + declared unit + geography + validity + source citation).
- **Normalisation:** map each source's fields to our module model; record declared unit and convert at calculation time, never at ingest.
- **Caching:** persist fetched records locally (keyed by source + record id + dataset version) to cut API calls and enable offline reuse; respect EPD validity dates.
- **Fallback chain:** selected EPD → cached EPD → generic default, with the UI always showing which tier was used.
- **Attribution & licensing:** store and display source attribution per the source's terms (required for EC3). Document data licences in the repo.

---

## 12. Data model

Core entities (suitable for in-memory + JSON persistence in v1; portable to a relational store later):

- **Project** — `id, name, building_type, gross_floor_area_m2, study_period_years, location, dataset_version, created_at, options[]`
- **Element** — `id, project_id, category (substructure/frame/envelope/finishes/services), name`
- **LineItem** — `id, element_id, material_name, quantity, unit, density?, transport_distance_km?, transport_mode?, wastage_rate?, factor_source_type (epd|generic|override), factor_record_id?, override_factors?, notes`
- **EmissionFactorSet** — `record_id, source (ec3|okobaudat|generic), declared_unit, gwp_by_module {A1A3, A4?, A5?, C1, C2, C3, C4}, geography, valid_until, citation`
- **ResultRow** — derived: `line_item_id, module_gwps{}, item_total`
- **ProjectResult** — derived: `embodied_gwp, operational_gwp, total_gwp, intensity_per_m2, breakdown_by_module, breakdown_by_element, data_quality_summary (epd vs generic counts)`

---

## 13. System architecture

Single Streamlit application, layered so the calculation core is independent of the UI and the data sources.

```
┌────────────────────────────────────────────┐
│ Streamlit UI (app.py + pages/)              │  project setup, inventory, results, compare
├────────────────────────────────────────────┤
│ Service layer                               │  orchestrates: build inventory → fetch factors → calculate
├───────────────┬───────────────┬─────────────┤
│ Calc engine   │ Data adapters │ Persistence  │
│ (pure Python, │ EC3 │ Öko │   │ JSON load/   │
│  unit-tested) │ Generic       │ save, cache  │
└───────────────┴───────────────┴─────────────┘
        │               │
   no I/O, pure     external EPD APIs (HTTP)
   functions
```

- **Calc engine** is pure functions (no network, no Streamlit) → fully unit-testable and reproducible. This is the heart of the product and the part that must be correct.
- **Data adapters** isolate each EPD source behind the common interface; adding a source = adding an adapter.
- **Service layer** wires inventory + factors + engine and applies the fallback chain.
- **Persistence** is JSON files locally + an on-disk factor cache; no database required for v1.

### Suggested repository layout
```
lca-carbon-calculator/
├── app.py                  # Streamlit entry
├── pages/                  # multipage UI (setup, inventory, results, compare)
├── lca/
│   ├── engine.py           # pure calculation functions (A,B6,C, aggregation)
│   ├── models.py           # dataclasses for entities above
│   ├── factors/
│   │   ├── base.py         # adapter interface + FactorCandidate/EmissionFactorSet
│   │   ├── ec3.py          # EC3/openEPD adapter
│   │   ├── okobaudat.py    # soda4LCA adapter
│   │   └── generic.py      # bundled default factors (CSV/JSON)
│   ├── cache.py            # local EPD cache
│   └── persistence.py      # project save/load (JSON)
├── data/
│   └── generic_factors.csv # bundled fallback factors (dated + sourced)
├── tests/
│   └── test_engine.py      # worked-example + module unit tests
├── requirements.txt
└── README.md
```

---

## 14. Tech stack

| Concern | Choice | Notes |
|---|---|---|
| Language | Python 3.11+ | |
| UI | Streamlit | multipage app; `st.session_state` for in-session model |
| Data handling | pandas | inventory tables, CSV import/export |
| Charts | Streamlit native / Plotly | stacked module bars, element breakdown |
| HTTP | `requests` (or `httpx`) | EPD API calls |
| Models | `dataclasses` / `pydantic` | typed entities, validation |
| Testing | `pytest` | engine unit tests are mandatory |
| Persistence | JSON files + on-disk cache | no DB in v1 |
| Deploy | Streamlit Community Cloud | free tier; secrets for API keys via `st.secrets` |

API keys (EC3) live in `st.secrets` / environment variables, never in the repo.

---

## 15. UX / primary flow

Multipage Streamlit app:

1. **Project setup** — name, building type, floor area, study period, location. Optional: start from template.
2. **Inventory** — add elements and line items in an editable table (`st.data_editor`); per-row: material search → pick EPD (or generic/override), quantity + unit, optional density/distance/wastage. Live data-quality indicator (how many rows are EPD-backed vs generic).
3. **Results** — headline total + intensity (kg CO₂e/m²); stacked bar by module; bar/table by element; embodied vs operational split; data-quality summary.
4. **Compare** — pick two options; side-by-side totals and per-module deltas.
5. **Export** — CSV (full line-item detail) + formatted report (HTML/PDF) organised by module.

UX principles: never hide provenance; generic/estimated values visually distinct from EPD-verified; every total drillable to inputs.

---

## 16. Success metrics

**Leading (days–weeks)**
- Time to first result for a new user with a 20-line BoQ — target < 15 min.
- % of line items backed by a specific EPD (vs generic) per completed project — target median ≥ 50% as a quality signal.
- Recalculation latency after an input change — target < 1 s for ≤200 lines.
- Task completion: % of started projects that reach a results view.

**Lagging (weeks–months)**
- Repeat use: projects created per returning user.
- Option-comparison usage: % of projects that create ≥2 options (indicates it's used for *decisions*, the core value).
- Qualitative: design teams reporting a material/structural change influenced by the tool.

> Targets above are hypotheses for a portfolio/MVP context, not benchmarked figures — validate with real usage before treating them as KPIs.

---

## 17. Risks & mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| EC3 API access terms / endpoints change (2.0 transition) | Integration breaks | Adapter isolation; Ökobaudat + generic fallback; pin to documented API version; re-verify before build |
| Users trust generic estimates as if EPD-verified | Misleading results | Hard UI distinction; data-quality summary; disclaimer on exports |
| Unit mismatches (declared unit vs entered unit) | Silent calculation errors | Explicit unit reconciliation + density; unit tests; validation that blocks ambiguous rows |
| Operational (B6) dominates and swamps embodied signal | Misreads design levers | Always show embodied vs operational split separately; allow B6 = 0 toggle for embodied-only screening |
| Out-of-date grid / transport factors | Inaccurate A4/B6 | Source defaults from official datasets, store the date, make them editable, show the source |
| Scope creep into a full certified LCA | Never ships | Explicit non-goals; phase gates; keep engine modular |

---

## 18. Open questions

- **[Data/Legal]** What are EC3's current production API terms and rate limits under the 2.0 program, and do attribution/notification requirements allow a public portfolio deployment? *(blocking for EC3 integration; non-blocking overall — Ökobaudat can ship first)*
- **[Data]** Which official source and vintage should supply default grid-electricity emission factors per region? *(blocking for B6 defaults)*
- **[Methodology]** For materials whose EPD reports end-of-life as a single combined C value, how should it be displayed — combined C, or apportioned to C1–C4? *(non-blocking; default to combined + note)*
- **[Methodology]** Default study period — 60 years assumed; confirm against the convention the target users expect. *(non-blocking)*
- **[Product]** Which element taxonomy (RICS / Uniclass / simplified custom) best fits the early-design user without overwhelming them? *(non-blocking; start simplified)*
- **[Data]** Source for any GWP/m² benchmark ranges (P2 feature) — needs a vetted, citable dataset before building. *(deferred)*

---

## 19. Roadmap / phasing

**Phase 1 — Calculation core (P0 engine + models)**
Pure engine for A1–A3, A4, A5, B6, C1–C4 + aggregation; dataclasses; bundled generic factors; full unit tests on the worked example. *Ships value even with manual factors.*

**Phase 2 — Streamlit MVP (P0 UI + one data source)**
Project setup, inventory editor, results dashboard, Ökobaudat (open, no-auth) integration, generic fallback, CSV export.

**Phase 3 — Comparison + EC3 + caching (P0/P1)**
Option duplication & side-by-side compare; EC3/openEPD adapter; local EPD cache; data-quality summary; formatted report export.

**Phase 4 — Polish & fast-follows (P1)**
CSV BoQ upload, templates, sensitivity view, project save/load.

**Future (P2)** — BIM/IFC import, B1–B5 service-life modelling, uncertainty ranges, benchmarking.

---

## 20. Appendix

### A. Glossary
- **GWP / kg CO₂e** — Global Warming Potential, the carbon-equivalent impact metric.
- **EPD** — Environmental Product Declaration; a verified document of a product's environmental impacts (EN 15804).
- **Embodied carbon** — emissions from materials & construction (modules A, C, and B1–B5); excludes operational energy.
- **Operational carbon** — emissions from running the building (B6 energy, B7 water).
- **Declared/functional unit** — the unit an EPD's impacts are stated per (kg, m³, m²…).
- **Cradle-to-gate** — A1–A3 only. **Cradle-to-grave** — A–C (and optionally D).

### B. Module coverage summary
In scope (v1): **A1–A3, A4, A5, B6, C1–C4.** Out of scope (v1): B1–B5, B7, D.

### C. References (verify against live/licensed sources)
- EN 15978:2011 — *Sustainability of construction works — Assessment of environmental performance of buildings — Calculation method* (CEN; paywalled).
- EN 15804 — *Sustainability of construction works — EPDs — Core rules for the product category of construction products* (CEN; paywalled).
- ISO 14040:2006 / ISO 14044:2006 — *Environmental management — Life cycle assessment* (ISO; paywalled).
- EC3 / Building Transparency — tool, API access & pricing, and openEPD docs: buildingtransparency.org, docs.buildingtransparency.org, openepd.buildingtransparency.org.
- ÖKOBAUDAT — oekobaudat.de (data + software-developer guidance); soda4LCA service (soda4lca.io).

> All standard clause details and emission-factor values must be confirmed against licensed standards and official EPD/database records before any non-screening use.
