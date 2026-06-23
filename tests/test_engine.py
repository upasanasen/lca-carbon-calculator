import unittest

from lca.engine import calculate_line_item, calculate_project, convert_quantity
from lca.models import EmissionFactorSet, LineItem, Project, module_dict


def factor(**values):
    modules = module_dict()
    modules.update(values)
    return EmissionFactorSet(
        record_id="test-factor",
        source="test",
        source_type="override",
        declared_unit="kg",
        gwp_by_module=modules,
        material_name="Test material",
        citation="PRD worked example",
    )


class EngineTests(unittest.TestCase):
    def test_prd_worked_example(self):
        project = Project(name="Worked example", default_transport_distance_km=50)
        item = LineItem(
            material_name="Test material",
            quantity=100000,
            unit="kg",
            transport_distance_km=50,
            transport_mode="road",
            wastage_rate=0.05,
            factor=factor(A1A3=0.12, C1=0.02),
        )

        row = calculate_line_item(item, project)

        self.assertAlmostEqual(row.module_gwps["A1A3"], 12000)
        self.assertAlmostEqual(row.module_gwps["A4"], 500)
        self.assertAlmostEqual(row.module_gwps["A5"], 600)
        self.assertAlmostEqual(row.module_gwps["C1"], 2000)
        self.assertAlmostEqual(row.total_gwp, 15100)

    def test_volume_to_mass_conversion_requires_density(self):
        converted, warnings = convert_quantity(10, "m3", "kg")
        self.assertIsNone(converted)
        self.assertIn("Density is required", warnings[0])

    def test_volume_to_mass_conversion_with_density(self):
        converted, warnings = convert_quantity(10, "m3", "kg", density_kg_per_m3=2400)
        self.assertEqual(warnings, [])
        self.assertAlmostEqual(converted, 24000)

    def test_project_b6_aggregation(self):
        project = Project(
            name="Operational",
            gross_floor_area_m2=100,
            study_period_years=60,
            energy_intensity_kwh_m2yr=10,
            grid_emission_factor_kgco2e_kwh=0.5,
        )
        result = calculate_project(project)
        self.assertAlmostEqual(result.module_totals["B6"], 30000)
        self.assertAlmostEqual(result.total_gwp, 30000)
        self.assertAlmostEqual(result.intensity_kgco2e_m2, 300)


if __name__ == "__main__":
    unittest.main()
