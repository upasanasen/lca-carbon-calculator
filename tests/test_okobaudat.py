"""Unit tests for the ÖKOBAUDAT parser using a captured fixture (no network).

The fixture mirrors the real soda4LCA `view=extended` JSON structure confirmed
against the live service, so the parsing logic is tested deterministically.
"""

import unittest

from lca.factors.okobaudat import parse_process, _norm_unit, _pick_gwp_result


FIXTURE = {
    "processInformation": {
        "quantitativeReference": {"referenceToReferenceFlow": [100342]},
        "time": {"referenceYear": "2023"},
    },
    "exchanges": {
        "exchange": [
            {
                "dataSetInternalID": 100342,
                "referenceFlow": True,
                "referenceToFlowDataSet": {
                    "shortDescription": [
                        {"lang": "en", "value": "Concrete C30/37"},
                        {"lang": "de", "value": "Beton C30/37"},
                    ]
                },
                "meanAmount": 1.0,
                "flowProperties": [
                    {"name": [{"lang": "en", "value": "Mass"}], "meanValue": 2400.0},
                    {
                        "name": [{"lang": "en", "value": "Volume"}],
                        "referenceFlowProperty": True,
                        "referenceUnit": "cbm",
                        "meanValue": 1.0,
                    },
                ],
            }
        ]
    },
    "LCIAResults": {
        "LCIAResult": [
            {
                "referenceToLCIAMethodDataSet": {
                    "shortDescription": [{"lang": "en", "value": "Climate change - total (GWP-total)"}]
                },
                "other": {
                    "anies": [
                        {"module": "A1-A3", "value": "300"},
                        {"module": "A4", "value": "9"},
                        {"module": "C3", "value": "10"},
                        {"module": "C4", "value": "5"},
                        {"module": "D", "value": "-20"},
                        {"name": "referenceToUnitGroupDataSet", "value": {"shortDescription": [{"value": "kg CO2 eq."}]}},
                    ]
                },
            }
        ]
    },
}


class OkobaudatParserTests(unittest.TestCase):
    def test_parse_declared_unit_and_modules(self):
        fs = parse_process(FIXTURE, record_id="uuid-123")
        self.assertEqual(fs.declared_unit, "m3")
        self.assertEqual(fs.source_type, "epd")
        self.assertAlmostEqual(fs.gwp_by_module["A1A3"], 300.0)
        self.assertAlmostEqual(fs.gwp_by_module["C3"], 10.0)
        self.assertAlmostEqual(fs.gwp_by_module["C4"], 5.0)
        # C1/C2 absent in fixture -> default 0
        self.assertAlmostEqual(fs.gwp_by_module["C1"], 0.0)

    def test_engine_modules_excluded_from_epd(self):
        """A4/A5/B6 and D must NOT be imported from the EPD (engine derives them)."""
        fs = parse_process(FIXTURE, record_id="uuid-123")
        self.assertAlmostEqual(fs.gwp_by_module["A4"], 0.0)  # fixture had A4=9, must be ignored
        self.assertAlmostEqual(fs.gwp_by_module["A5"], 0.0)
        self.assertAlmostEqual(fs.gwp_by_module["B6"], 0.0)

    def test_density_hint_from_mass_when_volume_declared(self):
        fs = parse_process(FIXTURE, record_id="uuid-123")
        self.assertAlmostEqual(fs.__dict__.get("density_kg_per_m3_hint"), 2400.0)

    def test_material_name_prefers_english(self):
        fs = parse_process(FIXTURE, record_id="uuid-123")
        self.assertEqual(fs.material_name, "Concrete C30/37")

    def test_unit_mapping(self):
        self.assertEqual(_norm_unit("qm"), "m2")
        self.assertEqual(_norm_unit("cbm"), "m3")
        self.assertEqual(_norm_unit("kg"), "kg")
        self.assertEqual(_norm_unit("Stück"), "each")

    def test_gwp_total_preferred_over_subcomponents(self):
        results = [
            {"referenceToLCIAMethodDataSet": {"shortDescription": [{"value": "GWP-fossil"}]}, "other": {"anies": []}},
            {"referenceToLCIAMethodDataSet": {"shortDescription": [{"value": "GWP-total"}]}, "other": {"anies": []}},
        ]
        picked = _pick_gwp_result(results)
        label = picked["referenceToLCIAMethodDataSet"]["shortDescription"][0]["value"]
        self.assertEqual(label, "GWP-total")


if __name__ == "__main__":
    unittest.main()
