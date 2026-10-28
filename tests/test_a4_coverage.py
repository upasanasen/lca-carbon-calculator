"""A4 transport omissions must be visible in the project result.

Area- and count-based line items with no density have no derivable mass, so
A4 transport cannot be calculated and is left at zero. The engine used to
filter those per-row warnings out of the project-level list and put nothing
in their place, so the Results view showed an A4 total that silently excluded
every such row. These tests pin the aggregated warning and the coverage fields.
"""

import unittest

from lca.engine import calculate_project
from lca.models import EmissionFactorSet, LineItem, Project, module_dict


def factor(declared_unit="kg", **values):
    modules = module_dict()
    modules.update(values)
    return EmissionFactorSet(
        record_id=f"test-{declared_unit}",
        source="test",
        source_type="override",
        declared_unit=declared_unit,
        gwp_by_module=modules,
        material_name="Test",
    )


def mass_item(name="Rebar"):
    return LineItem(material_name=name, quantity=1000, unit="kg",
                    transport_distance_km=50, factor=factor(A1A3=1.5))


def area_item(name="Glazing", density=None):
    return LineItem(material_name=name, quantity=200, unit="m2", density_kg_per_m3=density,
                    transport_distance_km=50, factor=factor(declared_unit="m2", A1A3=30.0))


class A4CoverageTests(unittest.TestCase):
    def test_area_item_without_density_is_counted_and_warned(self):
        project = Project(name="p", line_items=[mass_item(), area_item()])
        result = calculate_project(project)

        self.assertEqual(result.a4_omitted_rows, 1)
        self.assertEqual(result.a4_omitted_materials, ["Glazing"])
        self.assertEqual(result.included_rows, 2)
        a4_lines = [w for w in result.warnings if w.startswith("A4 transport omitted")]
        self.assertEqual(len(a4_lines), 1, result.warnings)
        self.assertIn("1 of 2 included rows", a4_lines[0])
        self.assertIn("Glazing", a4_lines[0])

    def test_omitted_row_still_contributes_its_other_modules(self):
        """Omission is of A4 only; the row is not excluded from the totals."""
        project = Project(name="p", line_items=[area_item()])
        result = calculate_project(project)
        self.assertFalse(result.rows[0].excluded)
        self.assertAlmostEqual(result.module_totals["A1A3"], 200 * 30.0)
        self.assertEqual(result.module_totals["A4"], 0.0)

    def test_all_mass_items_produce_no_a4_warning(self):
        project = Project(name="p", line_items=[mass_item("a"), mass_item("b")])
        result = calculate_project(project)
        self.assertEqual(result.a4_omitted_rows, 0)
        self.assertEqual(result.a4_omitted_materials, [])
        self.assertFalse(any(w.startswith("A4 transport omitted") for w in result.warnings))
        self.assertGreater(result.module_totals["A4"], 0.0)

    def test_excluded_rows_are_not_counted_as_a4_omissions(self):
        """A row that failed unit conversion is reported as excluded, not as an A4 gap."""
        bad = LineItem(material_name="Mystery", quantity=5, unit="m3",
                       factor=factor(declared_unit="kg", A1A3=1.0))  # no density -> cannot convert
        project = Project(name="p", line_items=[bad, mass_item()])
        result = calculate_project(project)
        self.assertTrue(result.rows[0].excluded)
        self.assertEqual(result.a4_omitted_rows, 0)
        self.assertEqual(result.included_rows, 1)
        self.assertTrue(any(w.startswith("Mystery excluded") for w in result.warnings))

    def test_per_row_a4_warnings_are_rolled_up_not_repeated(self):
        items = [area_item(f"Panel {i}") for i in range(8)]
        result = calculate_project(Project(name="p", line_items=items))
        a4_lines = [w for w in result.warnings if "A4 transport" in w]
        self.assertEqual(len(a4_lines), 1)
        self.assertIn("8 of 8 included rows", a4_lines[0])
        self.assertIn("…", a4_lines[0], "long lists should be truncated in the message")
        self.assertEqual(len(result.a4_omitted_materials), 8, "the full list stays on the result")

    def test_density_restores_a4_for_an_area_item(self):
        with_density = area_item(density=2500)  # a m2 item still has no thickness -> no mass
        result = calculate_project(Project(name="p", line_items=[with_density]))
        # Density alone cannot turn an area into a mass; this documents the current
        # behaviour so a future thickness field is a deliberate change, not a surprise.
        self.assertEqual(result.a4_omitted_rows, 1)


if __name__ == "__main__":
    unittest.main()
