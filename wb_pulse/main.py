"""Точка входа.

python -m wb_pulse.main --demo --once   показать работу на тестовых данных
python -m wb_pulse.main --once          один проход по реальному кабинету (для cron)
python -m wb_pulse.main                 работать постоянно
"""
import argparse
import time
from datetime import datetime, timedelta, timezone

from . import config, logic
from .notify import Notifier
from .sheets import Sheets
from .state import State
from .wb_client import DemoClient, WBClient, WBError


def check_orders(cfg, wb, state, tg, sheets):
    started = datetime.now(timezone.utc)
    # берём с запасом 10 минут: WB иногда добавляет заказы задним числом
    orders = wb.orders(state.last_check - timedelta(minutes=10))
    new = logic.pick_new_orders(orders, state.seen_orders)
    cancels = logic.pick_new_cancels(orders, state.seen_cancels)

    if state.first_run and not cfg.demo:
        # первый запуск на реальном кабинете: не засыпаем чат заказами за сутки, шлём одну сводку
        if orders:
            tg.send("WB Pulse подключён ✅\nЗа последние сутки:\n" + logic.daily_summary(orders))
    else:
        for o in new:
            tg.send(logic.format_order(o))
        for o in cancels:
            tg.send(logic.format_cancel(o))

    sheets.append_orders(new + cancels)
    state.seen_orders |= {o["srid"] for o in new}
    state.seen_cancels |= {o["srid"] for o in cancels}
    state.last_check = started
    state.first_run = False
    print(f"[{started:%H:%M:%S}] заказов в ответе: {len(orders)}, новых: {len(new)}, отмен: {len(cancels)}")


def check_stocks(cfg, wb, state, tg, sheets):
    summary = logic.stock_by_article(wb.stocks())
    low, state.low_alerted = logic.pick_low_stock(summary, cfg.low_stock, state.low_alerted)
    if low:
        tg.send(logic.format_low_stock(low, cfg.low_stock))
    sheets.write_stocks(summary, cfg.low_stock)
    print(f"позиций на складах: {len(summary)}, заканчивается (новых предупреждений): {len(low)}")


def main():
    ap = argparse.ArgumentParser(description="WB Pulse: заказы и остатки Wildberries в Telegram и Google Таблицу")
    ap.add_argument("--demo", action="store_true", help="тестовые данные вместо реального кабинета")
    ap.add_argument("--once", action="store_true", help="один проход и выход")
    args = ap.parse_args()

    cfg = config.load(demo=args.demo)
    wb = DemoClient() if cfg.demo else WBClient(cfg.wb_token)
    state = State("demo_state.json" if cfg.demo else cfg.state_file)
    tg = Notifier(cfg.tg_token, cfg.tg_chat_id)
    sheets = Sheets(cfg.sheet_id, cfg.google_creds)

    next_orders = next_stocks = 0.0
    while True:
        now = time.monotonic()
        try:
            if now >= next_orders:
                check_orders(cfg, wb, state, tg, sheets)
                next_orders = now + cfg.orders_every_min * 60
            if now >= next_stocks:
                if not cfg.demo:
                    time.sleep(61)  # лимит WB: 1 запрос в минуту на метод, разводим запросы
                check_stocks(cfg, wb, state, tg, sheets)
                next_stocks = time.monotonic() + cfg.stocks_every_min * 60
            state.save()
        except WBError as e:
            print(f"Ошибка WB: {e}")
            if args.once:
                raise SystemExit(1)
        except Exception as e:  # сеть упала или Telegram недоступен: ждём и пробуем снова
            print(f"Ошибка: {e!r}")
            if args.once:
                raise
        if args.once:
            break
        time.sleep(30)


if __name__ == "__main__":
    main()
