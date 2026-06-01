from __future__ import annotations

import cgi
import json
import mimetypes
import tempfile
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import db, service
from .config import BASE_TYPES, WEB_DIR


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        route = urlparse(self.path).path
        if route == "/api/dashboard":
            return self.json(service.dashboard())
        if route == "/api/imports":
            return self.json(db.imports())
        if route == "/api/shelf":
            return self.json(db.shelf_rules())
        if route == "/api/runs":
            return self.json(db.runs())
        if route == "/api/validations":
            query = parse_qs(urlparse(self.path).query)
            return self.json(db.validation_rows(int(query["run_id"][0])) if query.get("run_id") else db.validation_rows())
        if route == "/api/export":
            return self.send_bytes(service.export_history(),
                                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   "historico_conferencia.xlsx")
        return self.static(route)

    def do_POST(self):
        route = urlparse(self.path).path
        try:
            if route == "/api/import":
                fields, files = self.multipart()
                base_type = fields.get("base_type", "")
                if base_type not in BASE_TYPES:
                    raise ValueError("Selecione uma base valida.")
                results = [service.import_base(base_type, name, path) for name, path in files]
                return self.json(results, HTTPStatus.CREATED)
            if route == "/api/process":
                _, files = self.multipart()
                results = [service.process_txt(name, path) for name, path in files]
                return self.json(results, HTTPStatus.CREATED)
            if route == "/api/shelf":
                payload = self.json_body()
                cliente = str(payload.get("cliente", "")).strip()
                if not cliente:
                    raise ValueError("Informe o cliente.")
                db.upsert_shelf(
                    cliente,
                    float(str(payload["shelf_minimo"]).replace(",", ".")),
                    str(payload.get("cliente_nome", "")).strip(),
                    bool(payload.get("active", True)),
                )
                return self.json({"ok": True}, HTTPStatus.CREATED)
            return self.json({"error": "Rota nao encontrada."}, HTTPStatus.NOT_FOUND)
        except (ValueError, KeyError) as exc:
            return self.json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def json(self, payload, status=HTTPStatus.OK):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_bytes(self, body: bytes, content_type: str, filename: str):
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def json_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length) or b"{}")

    def multipart(self):
        content_type, params = cgi.parse_header(self.headers.get("Content-Type", ""))
        if content_type != "multipart/form-data":
            raise ValueError("Envie os arquivos como formulario.")
        params["boundary"] = params["boundary"].encode()
        params["CONTENT-LENGTH"] = int(self.headers.get("Content-Length", 0))
        form = cgi.FieldStorage(fp=self.rfile, headers=self.headers,
                                environ={"REQUEST_METHOD": "POST"}, keep_blank_values=True)
        fields, files = {}, []
        for key in form:
            items = form[key] if isinstance(form[key], list) else [form[key]]
            for item in items:
                if item.filename:
                    suffix = Path(item.filename).suffix
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
                        temp.write(item.file.read())
                        files.append((Path(item.filename).name, Path(temp.name)))
                else:
                    fields[key] = item.value
        if not files:
            raise ValueError("Selecione ao menos um arquivo.")
        return fields, files

    def static(self, route: str):
        relative = "index.html" if route in ("", "/") else route.lstrip("/")
        path = (WEB_DIR / relative).resolve()
        if WEB_DIR.resolve() not in path.parents and path != WEB_DIR.resolve():
            return self.json({"error": "Arquivo nao encontrado."}, HTTPStatus.NOT_FOUND)
        if not path.is_file():
            return self.json({"error": "Arquivo nao encontrado."}, HTTPStatus.NOT_FOUND)
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    service.initialize()
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print("Conferencia Logistica disponivel em http://localhost:8000")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor encerrado.")


if __name__ == "__main__":
    main()
