"""Отправка в Telegram. Без токена печатает в консоль, удобно для проверки."""
import requests


class Notifier:
    def __init__(self, token: str, chat_id: str):
        self.token, self.chat_id = token, chat_id

    @property
    def dry(self) -> bool:
        return not (self.token and self.chat_id)

    def send(self, text: str):
        if self.dry:
            print("\n----- Telegram (без токена, вывод в консоль) -----\n" + text)
            return
        resp = requests.post(
            f"https://api.telegram.org/bot{self.token}/sendMessage",
            json={"chat_id": self.chat_id, "text": text[:4096], "disable_web_page_preview": True},
            timeout=20,
        )
        if not resp.ok:
            print(f"Telegram не принял сообщение: {resp.status_code} {resp.text[:200]}")
