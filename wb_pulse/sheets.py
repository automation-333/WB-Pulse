"""Выгрузка в Google Таблицу через сервисный аккаунт (библиотека gspread).

Лист «Заказы» дополняется новыми строками, лист «Остатки» перезаписывается целиком.
Если SHEET_ID или GOOGLE_CREDS не заданы, выгрузка просто пропускается.
"""

ORDER_COLS = ["date", "srid", "supplierArticle", "techSize", "subject", "brand", "finishedPrice", "priceWithDisc", "warehouseName", "regionName", "isCancel"]
ORDER_HEAD = ["Дата", "ID заказа", "Артикул", "Размер", "Предмет", "Бренд", "Цена покупателя", "Цена со скидкой", "Склад", "Регион", "Отмена"]


class Sheets:
    def __init__(self, sheet_id: str, creds_path: str):
        self.enabled = bool(sheet_id and creds_path)
        if not self.enabled:
            return
        import gspread  # импорт здесь, чтобы без таблиц библиотека была не нужна
        self.book = gspread.service_account(filename=creds_path).open_by_key(sheet_id)

    def _sheet(self, title: str, head: list):
        import gspread
        try:
            ws = self.book.worksheet(title)
        except gspread.WorksheetNotFound:
            ws = self.book.add_worksheet(title=title, rows=1000, cols=len(head))
            ws.append_row(head)
        return ws

    def append_orders(self, orders: list):
        if not self.enabled or not orders:
            return
        rows = [[o.get(c, "") for c in ORDER_COLS] for o in orders]
        self._sheet("Заказы", ORDER_HEAD).append_rows(rows, value_input_option="USER_ENTERED")

    def write_stocks(self, summary: dict, threshold: int):
        if not self.enabled:
            return
        head = ["Артикул", "Размер", "Предмет", "Остаток, шт", "Статус", "По складам"]
        rows = [head]
        for (article, size), item in sorted(summary.items(), key=lambda x: x[1]["qty"]):
            status = "заканчивается" if item["qty"] <= threshold else "ок"
            by_wh = ", ".join(f"{w}: {q}" for w, q in item["warehouses"].items() if q > 0)
            rows.append([article, size, item["subject"], item["qty"], status, by_wh])
        ws = self._sheet("Остатки", head)
        ws.clear()
        ws.update(rows, "A1")
