import unittest

from app.parsers import canonicalize, normalize_customer_id


class ParserTest(unittest.TestCase):
    def test_maps_material_columns_from_real_files(self):
        factory = canonicalize({"Material": "96483", "Lote": "B09126B02"})
        detail = canonicalize({"ITEM": "96483"})
        blocked = canonicalize({"Material": "96483", "Lote": "B09126B02"})
        self.assertEqual(factory["produto"], detail["produto"])
        self.assertEqual(blocked["produto"], detail["produto"])
        self.assertEqual(blocked["lote"], factory["lote"])

    def test_normalizes_valid_cnpj_missing_leading_zero(self):
        self.assertEqual(normalize_customer_id("1992041000174"), "01992041000174")
        self.assertEqual(normalize_customer_id("3591002002053"), "03591002002053")

    def test_preserves_internal_customer_code(self):
        self.assertEqual(normalize_customer_id("10014047"), "10014047")
        self.assertEqual(normalize_customer_id("DMA_021"), "DMA_021")

    def test_removes_excel_decimal_suffix_from_identifiers(self):
        self.assertEqual(canonicalize({"ITEM": "96483.0"})["produto"], "96483")

    def test_removes_excel_text_marker(self):
        self.assertEqual(normalize_customer_id("'1992041000174"), "01992041000174")


if __name__ == "__main__":
    unittest.main()
