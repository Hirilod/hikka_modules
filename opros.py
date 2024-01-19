# ---------------------------------------------------------------------------------
#  /\_/\  🌐 This module was loaded through https://t.me/hikkamods_bot
# ( o.o )  🔐 Licensed under the GNU AGPLv3.
#  > ^ <   ⚠️ Owner of heta.hikariatama.ru doesn't take any responsibilities or intellectual property rights regarding this script
# ---------------------------------------------------------------------------------
# Name: poll_winner
# Author: hirilod
# requires: re
# Commands:
# .poll
# ---------------------------------------------------------------------------------



import random
from telethon.tl.types import Message, InputMediaPoll, Poll, PollAnswer

from .. import loader, utils
import re
@loader.tds
class Poll(loader.Module):
    strings = {
        'name': 'Poll',
        'poll': '<reply> - создает опрос из победителей игры.',
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
        '''<reply> - создает опрос из победителей игры.'''
        args = utils.get_args_raw(message)
        if not args:
            name_poll = 'Кто победитель'
        else:
            await utils.answer(message, args)
            name_poll = args
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
                question=name_poll,
                answers=polls
            )))
        except:
            await utils.answer(message, self.strings("no_answers"))
        