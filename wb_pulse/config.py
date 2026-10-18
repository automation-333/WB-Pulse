"""Настройки берутся из переменных окружения (файл .env)."""
import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # python-dotenv необязателен
    pass


@dataclass
class Config:
    wb_token: str              # токен API WB с доступом к «Статистике»
    tg_token: str              # токен Telegram-бота от @BotFather
    tg_chat_id: str            # куда слать уведомления (личка или группа)
    low_stock: int             # порог «товар заканчивается», шт.
    orders_every_min: int      # как часто проверять заказы (лимит WB: 1 запрос в минуту)
    stocks_every_min: int      # как часто проверять остатки (WB обновляет раз в 30 минут)
    state_file: str            # где хранить, какие заказы уже отправили
    sheet_id: str              # ID Google Таблицы (необязательно)
    google_creds: str          # путь к JSON сервисного аккаунта Google (необязательно)
    demo: bool                 # работать на тестовых данных без WB


def load(demo: bool = False) -> Config:
    env = os.environ.get
    return Config(
        wb_token=env("WB_TOKEN", ""),
        tg_token=env("TG_TOKEN", ""),
        tg_chat_id=env("TG_CHAT_ID", ""),
        low_stock=int(env("LOW_STOCK", "5")),
        orders_every_min=max(1, int(env("ORDERS_EVERY_MIN", "5"))),
        stocks_every_min=max(30, int(env("STOCKS_EVERY_MIN", "30"))),
        state_file=env("STATE_FILE", "state.json"),
        sheet_id=env("SHEET_ID", ""),
        google_creds=env("GOOGLE_CREDS", ""),
        demo=demo or env("DEMO", "") == "1",
    )
