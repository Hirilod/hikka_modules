import random
from telethon.tl.types import Message, InputMediaPoll, Poll, PollAnswer

from .. import loader, utils
import asyncio
import re
@loader.tds
class Test(loader.Module):
    strings = {
        'name': 'Test',
        'test': 'Выводит тестовое сообщение',
        "no_reply": (
            "<emoji document_id=5312526098750252863>🚫</emoji> <b>Нужен ответ на"
            " результат игры!</b>"
        ),
        "no_answers": (
            "<emoji document_id=5197183257367552085>😢</emoji> <b>В этом сообщении"
            " нету результатов.</b>"
        ),
        
    }
    
    
    @loader.command(ru_doc='Тест', en_doc='Test')
    async def test_comm(self, message: Message):
        args = utils.get_args_raw(message)
        if not args:
            win = 'Кто победитель'
        else:
            win = args
        reply = await message.get_reply_message()
        if not reply:
            await utils.answer(message, self.strings("no_reply"))
            return
        try:
            pattern = re.compile(r'\d+\.\s+(.+?)\s+-\s+(.+)')
            matches = pattern.findall(reply.raw_text)
            winners = {name: role for name, role in matches}
            polls = []
            i = 0
            for name, role in winners.items():
                i += 1
                polls.append(PollAnswer(f'{name} - {role}', str(i)))

            await utils.answer_file(message, file=InputMediaPoll(poll=Poll(
                id = random.randint(1, 9999999),
                question=win,
                answers=polls
            )))
        except:
            await utils.answer(message, self.strings("no_answers"))
        