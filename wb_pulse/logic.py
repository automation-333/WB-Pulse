"""Вся бизнес-логика без сети и файлов, поэтому её легко тестировать."""
from collections import defaultdict


def rub(x: float) -> str:
    return f"{round(x):,}".replace(",", " ") + " ₽"


def pick_new_orders(orders: list, seen: set) -> list:
    """Заказы, о которых ещё не сообщали. Ключ заказа в WB: srid.

    WB может вернуть один и тот же заказ повторно (например, когда он меняется),
    поэтому сравниваем с уже отправленными. Отменённые не шлём как новые.
    """
    fresh, batch = [], set()
    for o in orders:
        srid = o.get("srid")
        if not srid or srid in seen or srid in batch or o.get("isCancel"):
            continue
        batch.add(srid)
        fresh.append(o)
    return fresh


def pick_new_cancels(orders: list, seen_cancels: set) -> list:
    """Отмены, о которых ещё не сообщали."""
    out, batch = [], set()
    for o in orders:
        srid = o.get("srid")
        if o.get("isCancel") and srid and srid not in seen_cancels and srid not in batch:
            batch.add(srid)
            out.append(o)
    return out


def stock_by_article(stocks: list) -> dict:
    """Сводим остатки со всех складов по артикулу и размеру.

    Возвращает {(артикул, размер): {"qty": доступно, "warehouses": {склад: шт}, "subject": ..., "nmId": ...}}
    """
    out = defaultdict(lambda: {"qty": 0, "warehouses": {}, "subject": "", "nmId": None})
    for s in stocks:
        key = (s.get("supplierArticle", "?"), s.get("techSize", "0"))
        item = out[key]
        qty = int(s.get("quantity", 0) or 0)
        item["qty"] += qty
        item["warehouses"][s.get("warehouseName", "?")] = item["warehouses"].get(s.get("warehouseName", "?"), 0) + qty
        item["subject"] = s.get("subject", item["subject"])
        item["nmId"] = s.get("nmId", item["nmId"])
    return dict(out)


def pick_low_stock(summary: dict, threshold: int, alerted: set) -> tuple:
    """Какие позиции заканчиваются и о каких ещё не предупреждали.

    Возвращает (новые_предупреждения, обновлённый_набор_alerted).
    Если товар пополнили выше порога, убираем его из alerted, чтобы предупредить снова в следующий раз.
    """
    low, still_alerted = [], set()
    for key, item in summary.items():
        tag = f"{key[0]}|{key[1]}"
        if item["qty"] <= threshold:
            still_alerted.add(tag)
            if tag not in alerted:
                low.append((key, item))
    low.sort(key=lambda x: x[1]["qty"])
    return low, still_alerted


def format_order(o: dict) -> str:
    size = o.get("techSize")
    size_txt = f", размер {size}" if size and size != "0" else ""
    return (
        f"🛒 Новый заказ\n"
        f"{o.get('subject', 'Товар')} · {o.get('brand', '')}\n"
        f"Артикул {o.get('supplierArticle', '?')}{size_txt}\n"
        f"Цена для покупателя: {rub(o.get('finishedPrice') or o.get('priceWithDisc') or 0)}\n"
        f"Склад: {o.get('warehouseName', '?')} · {o.get('regionName', '')}\n"
        f"{o.get('date', '')[:16].replace('T', ' ')} МСК"
    )


def format_cancel(o: dict) -> str:
    return f"↩️ Отмена заказа\nАртикул {o.get('supplierArticle', '?')} · {rub(o.get('finishedPrice') or o.get('priceWithDisc') or 0)}"


def format_low_stock(low: list, threshold: int) -> str:
    lines = [f"⚠️ Заканчивается товар (порог {threshold} шт.)"]
    for (article, size), item in low:
        size_txt = f" [{size}]" if size and size != "0" else ""
        top = ", ".join(f"{w}: {q}" for w, q in sorted(item["warehouses"].items(), key=lambda x: -x[1]) if q > 0) or "нигде нет"
        lines.append(f"• {article}{size_txt}: {item['qty']} шт. ({top})")
    return "\n".join(lines)


def daily_summary(orders: list) -> str:
    """Короткая сводка по заказам за период: количество, выручка, отмены, топ товаров."""
    # WB может прислать один заказ несколько раз: оставляем последнюю версию каждого srid
    latest = {}
    for o in orders:
        latest[o.get("srid") or id(o)] = o
    orders = list(latest.values())
    live = [o for o in orders if not o.get("isCancel")]
    cancels = len(orders) - len(live)
    revenue = sum(o.get("finishedPrice") or o.get("priceWithDisc") or 0 for o in live)
    top = defaultdict(int)
    for o in live:
        top[o.get("supplierArticle", "?")] += 1
    top_txt = ", ".join(f"{a} ({n})" for a, n in sorted(top.items(), key=lambda x: -x[1])[:3]) or "нет"
    return f"📊 Заказов: {len(live)} · выручка {rub(revenue)} · отмен: {cancels}\nТоп: {top_txt}"
