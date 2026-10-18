import json
import os
import tempfile
import unittest
from pathlib import Path

from wb_pulse import logic
from wb_pulse.state import State

DEMO = Path(__file__).resolve().parent.parent / "demo_data"
ORDERS = json.loads((DEMO / "orders.json").read_text(encoding="utf-8"))
STOCKS = json.loads((DEMO / "stocks.json").read_text(encoding="utf-8"))


class TestOrders(unittest.TestCase):
    def test_duplicates_and_cancels_are_skipped(self):
        new = logic.pick_new_orders(ORDERS, set())
        # 5 строк: одна повторяется, одна отмена, значит новых 3
        self.assertEqual([o["srid"] for o in new], ["demo.7f3a1c", "demo.91be4d", "demo.c04e88"])

    def test_already_sent_orders_are_not_sent_again(self):
        new = logic.pick_new_orders(ORDERS, {"demo.7f3a1c", "demo.91be4d", "demo.c04e88"})
        self.assertEqual(new, [])

    def test_cancel_reported_once(self):
        first = logic.pick_new_cancels(ORDERS, set())
        self.assertEqual([o["srid"] for o in first], ["demo.5d2f10"])
        self.assertEqual(logic.pick_new_cancels(ORDERS, {"demo.5d2f10"}), [])

    def test_order_without_srid_is_ignored(self):
        self.assertEqual(logic.pick_new_orders([{"supplierArticle": "X"}], set()), [])


class TestStocks(unittest.TestCase):
    def test_stock_is_summed_across_warehouses(self):
        s = logic.stock_by_article(STOCKS)
        self.assertEqual(s[("HD-OVR-BLK", "L")]["qty"], 3)
        self.assertEqual(s[("CAP-LOGO-GRN", "0")]["qty"], 58)

    def test_low_stock_alert_once_then_rearm_after_restock(self):
        s = logic.stock_by_article(STOCKS)
        low, alerted = logic.pick_low_stock(s, 5, set())
        self.assertEqual({k for k, _ in low}, {("HD-OVR-BLK", "L"), ("TSH-BASIC-WHT", "M")})
        # повторная проверка: те же позиции, предупреждений больше нет
        low2, alerted = logic.pick_low_stock(s, 5, alerted)
        self.assertEqual(low2, [])
        # пополнили худи L до 30 шт.: снимаем его из «уже предупреждали»
        s[("HD-OVR-BLK", "L")]["qty"] = 30
        _, alerted = logic.pick_low_stock(s, 5, alerted)
        self.assertNotIn("HD-OVR-BLK|L", alerted)
        # снова кончилось: предупреждаем заново
        s[("HD-OVR-BLK", "L")]["qty"] = 1
        low3, _ = logic.pick_low_stock(s, 5, alerted)
        self.assertEqual([k for k, _ in low3], [("HD-OVR-BLK", "L")])


class TestFormat(unittest.TestCase):
    def test_money_format(self):
        self.assertEqual(logic.rub(2785.4), "2 785 ₽")

    def test_summary(self):
        text = logic.daily_summary(ORDERS)
        # 5 строк: повтор считается один раз, значит 3 заказа и 1 отмена
        self.assertIn("Заказов: 3", text)
        self.assertIn("отмен: 1", text)
        self.assertIn("HD-OVR-BLK", text)


class TestState(unittest.TestCase):
    def test_state_survives_restart(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "state.json")
            st = State(path)
            self.assertTrue(st.first_run)
            st.seen_orders.add("abc")
            st.save()
            st2 = State(path)
            self.assertFalse(st2.first_run)
            self.assertIn("abc", st2.seen_orders)


if __name__ == "__main__":
    unittest.main()
