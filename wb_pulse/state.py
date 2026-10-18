"""Память бота между запусками: что уже отправили, чтобы не слать дубли после перезапуска."""
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone


class State:
    def __init__(self, path: str):
        self.path = path
        data = {}
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        self.seen_orders = set(data.get("seen_orders", []))
        self.seen_cancels = set(data.get("seen_cancels", []))
        self.low_alerted = set(data.get("low_alerted", []))
        last = data.get("last_check")
        # первый запуск: смотрим заказы за последние сутки, но не шлём их все подряд (см. main.py)
        self.first_run = last is None
        self.last_check = datetime.fromisoformat(last) if last else datetime.now(timezone.utc) - timedelta(days=1)

    def save(self):
        data = {
            "seen_orders": sorted(self.seen_orders)[-20000:],
            "seen_cancels": sorted(self.seen_cancels)[-20000:],
            "low_alerted": sorted(self.low_alerted),
            "last_check": self.last_check.isoformat(),
        }
        # пишем во временный файл и подменяем: при сбое state.json не сломается
        folder = os.path.dirname(os.path.abspath(self.path))
        fd, tmp = tempfile.mkstemp(dir=folder, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.path)
