import http.client
import json
import tempfile
import threading
import unittest
import uuid
from pathlib import Path

from app import db, service
from app.server import Handler, ThreadingHTTPServer


class HttpTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        db.DATA_DIR = root
        db.UPLOAD_DIR = root / "uploads"
        db.DB_PATH = root / "test.db"
        service.UPLOAD_DIR = db.UPLOAD_DIR
        service.initialize()
        self.root = root
        self._import_fixtures()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.temp.cleanup()

    def test_processes_txt_upload(self):
        boundary = "----" + uuid.uuid4().hex
        body = (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="files"; filename="ok.txt"\r\n'
            "Content-Type: text/plain\r\n\r\n"
            "01/05/2026;10:00:00;PAL-1;10\r\n"
            f"--{boundary}--\r\n"
        ).encode()
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port)
        connection.request("POST", "/api/process", body, {
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(body)),
        })
        response = connection.getresponse()
        payload = json.loads(response.read())
        connection.close()
        self.assertEqual(response.status, 201)
        self.assertEqual(payload[0]["approved"], 1)

    def test_exports_history_xlsx(self):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port)
        connection.request("GET", "/api/export")
        response = connection.getresponse()
        body = response.read()
        connection.close()
        self.assertEqual(response.status, 200)
        self.assertEqual(body[:4], b"PK\x03\x04")

    def _import_fixtures(self):
        self._import("fabrica", "f.csv",
                     "Chave Pallet;Material;Lote;Data do vencimento;Data de producao\n"
                     "PAL-1;100;LOT-1;01/01/2027;01/01/2026\n")
        self._import("detalhamento", "d.csv",
                     "REMESSA;CNPJ;NOME;ITEM;QTD_EMBALA\n"
                     "REM-1;CLI-1;Cliente Teste;100;10\n")
        self._import("bloqueados", "b.csv", "Material;Lote;Status\n999;OTHER;TRIAGEM\n")
        self._import("shelf", "s.csv", "Destino;Shelf;ID_Destino\nCLI-1;0,5;Cliente Teste\n")

    def _import(self, base_type, filename, content):
        path = self.root / filename
        path.write_text(content, encoding="utf-8")
        service.import_base(base_type, filename, path)


if __name__ == "__main__":
    unittest.main()
