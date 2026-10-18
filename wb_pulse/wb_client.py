"""Клиент Statistics API Wildberries.

Документация: https://dev.wildberries.ru/en/openapi/reports
- GET /api/v1/supplier/orders?dateFrom=...  заказы, лимит 1 запрос в минуту
- GET /api/v1/supplier/stocks?dateFrom=...  остатки, данные обновляются раз в 30 минут
Авторизация: заголовок Authorization с токеном из кабинета продавца.
"""
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

BASE_URL = "https://statistics-api.wildberries.ru"
MSK = timezone(timedelta(hours=3))  # даты WB отдаёт по Москве


class WBError(Exception):
    pass


class WBClient:
    def __init__(self, token: str, timeout: int = 30):
        if not token:
            raise WBError("Нет WB_TOKEN. Создайте токен в кабинете продавца: Настройки, Доступ к API, категория «Статистика».")
        self.session = requests.Session()
        self.session.headers["Authorization"] = token
        self.timeout = timeout

    def _get(self, path: str, params: dict) -> list:
        # Один повтор при 429: WB просит ждать, сколько указано в заголовке Retry-After
        for attempt in range(2):
            resp = self.session.get(BASE_URL + path, params=params, timeout=self.timeout)
            if resp.status_code == 429 and attempt == 0:
                time.sleep(int(resp.headers.get("X-Ratelimit-Retry", resp.headers.get("Retry-After", "60"))))
                continue
            if resp.status_code == 401:
                raise WBError("WB отклонил токен (401). Проверьте токен и что у него есть доступ к «Статистике».")
            if not resp.ok:
                raise WBError(f"WB ответил {resp.status_code}: {resp.text[:200]}")
            return resp.json() or []
        raise WBError("WB отвечает 429 даже после паузы: слишком частые запросы.")

    def orders(self, since: datetime) -> list:
        """Заказы, изменённые после since (включая отмены)."""
        return self._get("/api/v1/supplier/orders", {"dateFrom": since.astimezone(MSK).strftime("%Y-%m-%dT%H:%M:%S")})

    def stocks(self) -> list:
        """Текущие остатки по складам WB. Дата из прошлого отдаёт полный список."""
        return self._get("/api/v1/supplier/stocks", {"dateFrom": "2019-06-20T00:00:00"})


class DemoClient:
    """Те же методы, но данные из папки demo_data. Нужен для показа без кабинета продавца."""

    def __init__(self, folder: str = None):
        self.folder = Path(folder or Path(__file__).resolve().parent.parent / "demo_data")

    def orders(self, since: datetime) -> list:
        return json.loads((self.folder / "orders.json").read_text(encoding="utf-8"))

    def stocks(self) -> list:
        return json.loads((self.folder / "stocks.json").read_text(encoding="utf-8"))
