from __future__ import annotations

from collections import defaultdict
from datetime import date

from .parsers import parse_date, parse_number


def validate(txt_rows: list[dict], fabrica: list[dict], detalhamento: list[dict],
             bloqueados: list[dict], shelf_rules: list[dict]) -> list[dict]:
    factory_by_pallet = {row.get("palete", ""): row for row in fabrica}
    blocked_by_product_lot = {
        (row.get("produto", ""), row.get("lote", "")): _blocked_label(row)
        for row in bloqueados
    }
    shelf_by_customer = {
        row["cliente"]: float(row["shelf_minimo"])
        for row in shelf_rules if row.get("active", 1)
    }

    txt_totals = defaultdict(float)
    for row in txt_rows:
        factory = factory_by_pallet.get(row.get("palete", ""), {})
        product = factory.get("produto", "")
        if product:
            txt_totals[product] += parse_number(row.get("quantidade"))

    detail_by_shipment = _detail_totals(detalhamento)
    shipment = _identify_shipment(dict(txt_totals), detail_by_shipment)
    detail_totals = detail_by_shipment.get(shipment, {})

    results = []
    for row in txt_rows:
        errors = []
        pallet = row.get("palete", "")
        factory = factory_by_pallet.get(pallet)
        if not factory:
            factory = {}
            errors.append("PALETE_NAO_LOCALIZADO")
        product = factory.get("produto", "")
        lot = factory.get("lote", "")
        if not shipment:
            errors.append("REMESSA_NAO_IDENTIFICADA")

        qty_detail = detail_totals.get(product, 0)
        if shipment and product not in detail_totals:
            errors.append("ITEM_AUSENTE_NO_DETALHAMENTO")
        elif shipment and product and txt_totals[product] != qty_detail:
            errors.append("QUANTIDADE_DIVERGENTE")

        blocked_status = blocked_by_product_lot.get((product, lot), "")
        if blocked_status:
            errors.append("ITEM_BLOQUEADO")

        customers = _customers_for(shipment, product, detalhamento)
        minimums = [shelf_by_customer[customer["codigo"]] for customer in customers
                    if customer["codigo"] in shelf_by_customer]
        shelf_min = max(minimums) if minimums else None
        expiry = parse_date(factory.get("validade", ""))
        production = parse_date(factory.get("producao", ""))
        shipped = parse_date(row.get("data_embarque", ""))
        shelf_percent = _shelf_percentage(production, expiry, shipped)
        if product and not expiry:
            errors.append("VALIDADE_NAO_LOCALIZADA")
        if product and not production:
            errors.append("PRODUCAO_NAO_LOCALIZADA")
        if shipment and customers and shelf_min is None:
            errors.append("PARAMETRO_SHELF_NAO_CADASTRADO")
        elif shelf_min is not None and shelf_percent is not None and shelf_percent < shelf_min:
            errors.append("SHELF_LIFE_INSUFICIENTE")

        results.append({
            "data_embarque": shipped,
            "remessa": shipment,
            "cliente": ", ".join(customer["nome"] for customer in customers),
            "palete": pallet,
            "produto": product,
            "lote": lot,
            "validade": expiry,
            "producao": production,
            "quantidade_txt": parse_number(row.get("quantidade")),
            "quantidade_detalhe": qty_detail,
            "shelf_percentual": round(shelf_percent, 4) if shelf_percent is not None else None,
            "shelf_minimo": shelf_min,
            "bloqueio_status": blocked_status,
            "status": "APROVADO" if not errors else "DIVERGENCIA",
            "errors": ", ".join(errors),
        })
    return results


def _detail_totals(rows: list[dict]) -> dict[str, dict[str, float]]:
    totals = defaultdict(lambda: defaultdict(float))
    for row in rows:
        totals[row.get("remessa", "")][row.get("produto", "")] += parse_number(row.get("quantidade"))
    return {shipment: dict(products) for shipment, products in totals.items()}


def _identify_shipment(txt_totals: dict[str, float],
                       detail_by_shipment: dict[str, dict[str, float]]) -> str:
    if not txt_totals:
        return ""
    matches = [shipment for shipment, totals in detail_by_shipment.items() if totals == txt_totals]
    if len(matches) == 1:
        return matches[0]

    txt_products = set(txt_totals)
    candidates = []
    for shipment, totals in detail_by_shipment.items():
        detail_products = set(totals)
        overlap = len(txt_products & detail_products)
        if not overlap:
            continue
        difference = len(txt_products ^ detail_products)
        quantity_gap = sum(abs(txt_totals.get(product, 0) - totals.get(product, 0))
                           for product in txt_products | detail_products)
        candidates.append((overlap, -difference, -quantity_gap, shipment))
    if not candidates:
        return ""
    candidates.sort(reverse=True)
    return candidates[0][3] if len(candidates) == 1 or candidates[0][:3] != candidates[1][:3] else ""


def _customers_for(shipment: str, product: str, rows: list[dict]) -> list[dict]:
    customers = {}
    for row in rows:
        if row.get("remessa") == shipment and row.get("produto") == product:
            code = row.get("cliente", "")
            customers[code] = {"codigo": code, "nome": row.get("cliente_nome") or code}
    return list(customers.values())


def _shelf_percentage(production: str, expiry: str, shipped: str) -> float | None:
    try:
        produced_at = date.fromisoformat(production)
        expires_at = date.fromisoformat(expiry)
        shipped_at = date.fromisoformat(shipped)
    except (TypeError, ValueError):
        return None
    total_life = (expires_at - produced_at).days
    return (expires_at - shipped_at).days / total_life if total_life > 0 else None


def _blocked_label(row: dict) -> str:
    values = [row.get("status", ""), row.get("status_secundario", "")]
    return " | ".join(value for value in values if value)
