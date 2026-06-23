# LCA Carbon Calculator (EN 15978)

A Streamlit app for **early-stage whole-life carbon screening** of buildings,
structured by EN 15978 lifecycle modules. Enter building elements and material
quantities, pull emission factors from a live EPD database, and see global
warming potential (GWP, kg CO₂e) broken down by module and by element.

Built to the spec in [`PRD.md`](./PRD.md) (also `PRD.docx`). Standards context:
EN 15978 (building assessment) · EN 15804 (product EPDs) · ISO 14040/44 (LCA
framework).

## What it does

- **Pure-Python calculation engine** for modules **A1–A3, A4, A5, B6, C1–C4**
  with unit reconciliation (kg ↔ m³ via density, m², each).
- **Editable inventory** table (elements → line items) with transparent,
  per-row factor provenance.
- **Three factor sources**, blended with a clear trust hierarchy:
  1. **ÖKOBAUDAT (live EPD)** — primary external database, no API key.
  2. **Bundled generic seed factors** — offline fallback, *indicative only*.
  3. **Manual override** — type a value from a supplier datasheet, with a note.
  - Plus an **optional local openLCA** connector (see below).
- **Option comparison** (duplicate a design, compare module-by-module).
- **Exports**: line-item CSV and an EN 15978-structured HTML summary.
- **Save/load** projects as JSON.

## Data sources

### ÖKOBAUDAT (implemented, live)
`lca/factors/okobaudat.py` queries the German Federal **ÖKOBAUDAT** database
through its public **soda4LCA** REST API. Data is free and needs no API key, so
it works locally and on Streamlit Community Cloud. The adapter imports the
**GWP-total** indicator's **A1–A3** and **C1–C4** values and the declared unit
(kg / m² / m³ / piece). A4, A5 and B6 are intentionally **not** taken from the
EPD — the engine derives them from transport distance, wastage and operational
energy, so importing them would double-count.

> The soda4LCA endpoints and field structure were confirmed against the live
> service in June 2026. APIs change — re-verify before relying on results
> externally, and check each EPD's validity date and declared unit.

### Generic seed factors (implemented, indicative only)
`data/generic_factors.csv` ships a handful of common materials so the app runs
offline and out of the box. **These values are illustrative screening seeds for
development, not verified emission factors.** Replace them with EPD data (or a
manual override with a citation) before using any output externally. The UI
labels generic-backed rows distinctly from EPD-backed rows.

### Manual override (implemented)
Type A1–A3 / C factors directly into the inventory table and record the source
in the citation field. Rows are tagged `override`.

### openLCA (optional, local power-user path)
`lca/factors/openlca.py` can talk to a locally running **openLCA** desktop app
via its bundled IPC server (JSON-RPC on `127.0.0.1:8080`). This is an optional
extra beyond the PRD scope and only works **if** openLCA is installed on the
machine, a database has been imported, and the IPC server is started. The app's
**openLCA** tab detects this at runtime and reports what it actually finds — it
makes no assumptions about your setup. Mapping openLCA product systems into
EN 15978 module factors is database-specific and left as a follow-up.

To start the IPC server (after creating/importing a database in openLCA):

```bash
/Applications/openLCA.app/Contents/Eclipse/bin/ipc-server.sh "YOUR_DATABASE_NAME"
```

### EC3 / openEPD (documented future adapter, not yet implemented)
The PRD specifies EC3/openEPD as a second external source. It requires an EC3
account and API key and is **not** implemented here to avoid shipping untested,
key-gated code. The adapter interface (`lca/factors/base.py`) is designed so
EC3 can be added as a drop-in alongside ÖKOBAUDAT.

## Run

```bash
cd "lca-carbon-calculator"
pip install -r requirements.txt
streamlit run app.py
```

## Test

```bash
cd "lca-carbon-calculator"
python3 -m unittest discover -s tests -v
# or, if you have pytest installed: pytest -q
```

Tests cover the engine (including the PRD worked example: A1–A3 12,000 + A4 500
+ A5 600 + C 2,000 = 15,100 kg CO₂e) and the ÖKOBAUDAT JSON parser (against a
captured fixture, so no network is needed).

## Repository layout

```
lca-carbon-calculator/
├── app.py                    # Streamlit UI (Setup, Inventory, Results, Compare, Export, openLCA)
├── lca/
│   ├── engine.py             # pure calculation functions + aggregation
│   ├── models.py             # dataclasses (Project, LineItem, EmissionFactorSet, results)
│   ├── persistence.py        # JSON project save/load
│   └── factors/
│       ├── base.py           # adapter interface + FactorCandidate
│       ├── generic.py        # bundled indicative seed factors
│       ├── okobaudat.py      # ÖKOBAUDAT / soda4LCA live EPD adapter
│       └── openlca.py        # optional local openLCA IPC connector
├── data/generic_factors.csv  # indicative seed factors (NOT verified)
├── tests/                    # engine + ÖKOBAUDAT parser tests
├── requirements.txt
├── PRD.md / PRD.docx         # product requirements document
└── README.md
```

## Data-quality & honesty notes

- Generic seed factors are **indicative only** — never present them as verified.
- ÖKOBAUDAT results carry the source dataset's UUID and indicator in the
  citation; always confirm the EPD's validity date and declared unit.
- Default **grid** (B6) and **transport** (A4) factors must be replaced with
  official, dated sources before non-screening use; the app leaves the grid
  factor at 0 until you enter a sourced value.
- This is a **screening** tool for early-design decisions, not a verified
  EN 15978 assessment for certification or regulatory filing.
```
