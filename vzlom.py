from .. import loader, utils
import asyncio


@loader.tds
class FakeHackMod(loader.Module):
    """Фейковый взлом чата по команде .vzlom"""

    strings = {
        "name": "FakeHack",
    }

    async def client_ready(self, client, db):
        self.client = client

    async def vzlomcmd(self, message):
        """Запустить фейковый взлом текущего чата (30‒40 секунд)"""

        # Шаги «взлома» и соответствующий процент выполнения
        steps = [
            ("Сканирование списка админов…", 5),
            ("Получение прав админа…", 15),
            ("Удаление остальных админов…", 25),
            ("Смена названия чата…", 35),
            ("Сброс аватарки…", 45),
            ("Инъекция вируса \"Котики\"…", 55),
            ("Заливка коллекции стикеров…", 65),
            ("Очистка истории сообщений…", 75),
            ("Финальная стадия взлома…", 85),
            ("Закрепление контроля…", 95),
        ]

        # Отправляем стартовое сообщение
        prog_bar_len = 10  # ▓░ полоска из 10 символов
        msg = await utils.answer(message, "🚀 Начинаю взлом чата: [░" * prog_bar_len + "] 0%")

        total_duration = 34  # секунд, попадает в диапазон 30–40
        interval = total_duration / (len(steps) + 1)

        # Последовательно обновляем сообщение, имитируя прогресс
        for text, pct in steps:
            await asyncio.sleep(interval)
            filled = int(prog_bar_len * pct / 100)
            bar = "▓" * filled + "░" * (prog_bar_len - filled)
            await msg.edit(f"{text}\n[{bar}] {pct}%")

        # Финальный 100 %
        await asyncio.sleep(interval)
        bar = "▓" * prog_bar_len
        await msg.edit(f"✅ Взлом завершён!\n[{bar}] 100%")

        # Упоминание владельца юзербота
        me = await self.client.get_me()
        owner_mention = f"@{me.username}" if getattr(me, "username", None) else (me.first_name or "владелец")

        await asyncio.sleep(1)
        await msg.edit(f"{owner_mention}, успешно взломан, попущен и выебан в анал")
