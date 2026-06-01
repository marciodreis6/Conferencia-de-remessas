import unittest

from app.validation import validate


class ValidationTest(unittest.TestCase):
    def test_identifies_exact_shipment_and_approves_valid_pallet(self):
        results = validate(
            [{"data_embarque": "2026-05-01", "palete": "PAL-1", "quantidade": "10"}],
            [{"palete": "PAL-1", "produto": "100", "lote": "LOT-1",
              "producao": "2026-01-01", "validade": "2027-01-01"}],
            [{"remessa": "REM-1", "cliente": "CLI-1", "cliente_nome": "Cliente Teste",
              "produto": "100", "quantidade": "10"}],
            [],
            [{"cliente": "CLI-1", "shelf_minimo": 0.5, "active": 1}],
        )
        self.assertEqual(results[0]["remessa"], "REM-1")
        self.assertEqual(results[0]["status"], "APROVADO")
        self.assertEqual(results[0]["cliente"], "Cliente Teste")

    def test_blocks_by_material_and_lot_and_uses_strictest_shelf(self):
        results = validate(
            [{"data_embarque": "2026-10-01", "palete": "PAL-1", "quantidade": "10"}],
            [{"palete": "PAL-1", "produto": "100", "lote": "LOT-1",
              "producao": "2026-01-01", "validade": "2027-01-01"}],
            [
                {"remessa": "REM-1", "cliente": "CLI-1", "cliente_nome": "Cliente 1",
                 "produto": "100", "quantidade": "4"},
                {"remessa": "REM-1", "cliente": "CLI-2", "cliente_nome": "Cliente 2",
                 "produto": "100", "quantidade": "6"},
            ],
            [{"produto": "100", "lote": "LOT-1", "status": "TRIAGEM",
              "status_secundario": "FORA DO PRAZO"}],
            [
                {"cliente": "CLI-1", "shelf_minimo": 0.1, "active": 1},
                {"cliente": "CLI-2", "shelf_minimo": 0.5, "active": 1},
            ],
        )
        self.assertIn("ITEM_BLOQUEADO", results[0]["errors"])
        self.assertIn("SHELF_LIFE_INSUFICIENTE", results[0]["errors"])
        self.assertEqual(results[0]["shelf_minimo"], 0.5)

    def test_does_not_guess_shipment_when_composition_differs(self):
        results = validate(
            [{"data_embarque": "2026-05-01", "palete": "PAL-1", "quantidade": "9"}],
            [{"palete": "PAL-1", "produto": "100", "lote": "LOT-1",
              "producao": "2026-01-01", "validade": "2027-01-01"}],
            [{"remessa": "REM-1", "cliente": "CLI-1", "produto": "100", "quantidade": "10"}],
            [],
            [{"cliente": "CLI-1", "shelf_minimo": 0.5, "active": 1}],
        )
        self.assertEqual(results[0]["remessa"], "")
        self.assertIn("REMESSA_NAO_IDENTIFICADA", results[0]["errors"])


if __name__ == "__main__":
    unittest.main()

