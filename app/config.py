from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "logistica.db"
WEB_DIR = ROOT / "web"

BASE_TYPES = {
    "fabrica": {
        "label": "Relatorio da fabrica",
        "required": ["palete", "produto", "lote", "validade", "producao"],
    },
    "detalhamento": {
        "label": "Detalhamento de remessas",
        "required": ["remessa", "cliente", "produto", "quantidade"],
    },
    "bloqueados": {
        "label": "Itens bloqueados",
        "required": ["produto", "lote", "status"],
    },
    "shelf": {
        "label": "Parametros de shelf life",
        "required": ["cliente", "shelf_minimo"],
    },
}

ALIASES = {
    "palete": ["palete", "chave_palete", "chave pallet", "chave do palete", "pallet", "sscc"],
    "produto": ["produto", "codigo_produto", "cod produto", "material", "item", "sku"],
    "lote": ["lote", "batch", "numero_lote"],
    "validade": ["validade", "data_validade", "data do vencimento", "vencimento", "expiry"],
    "producao": ["producao", "produção", "data de produção", "data de producao"],
    "remessa": ["remessa", "numero_remessa", "shipment", "carga"],
    "cliente": ["cliente", "codigo_cliente", "customer", "cnpj", "destino"],
    "cliente_nome": ["nome", "id_destino", "nome cliente"],
    "quantidade": ["quantidade", "qtd", "qtde", "quantity", "qtd_embala", "qtd_cx_fd"],
    "quantidade_fabrica": ["qtd.  um registro"],
    "status": ["status", "situacao", "bloqueio"],
    "status_secundario": ["status²", "status2"],
    "shelf_minimo": ["shelf", "shelf_life_minimo", "shelf minimo"],
}
