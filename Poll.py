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
class Poll_winner(loader.Module):
    strings = {
        'name': 'Poll',
        'poll': '<reply> - создает опрос из победителей игры.',
        "no_reply": (
            "<emoji document_id=5312526098750252863>🚫</emoji> <b>Нужен ответ на"
            " результат игры!</b>"
        ),
        "no_answers": (
            "<emoji document_id=5197183257367552085>😢</emoji> <b>Неверно введены данные.</b>"
        ),
        "no_args": (
            "<emoji document_id=5312526098750252863>🚫</emoji> <b>Не указаны"
            " аргументы</b>"
        ),
        
    }
    
    
    @loader.command(ru_doc='<reply> - создает опрос из победителей игры.')
    async def poll(self, message: Message):
        '''<reply> [название опроса]/[номера игроков через пробел] - создает опрос из победителей игры.'''
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings("no_args"))
            return
        reply = await message.get_reply_message()
        if not reply:
            await utils.answer(message, self.strings("no_reply"))
            return
        
        try:
            win  = args.split('/')[0]
            players = (args.split('/')[1]).split(' ')
            pattern = re.compile(r'\d+\.\s+(.+?)\s+-\s+(.+)')
            matches = pattern.findall(reply.raw_text)
            
            # winners = {name: role for name, role in matches}
            polls = []
            i = 0
            for player in players:
                i += 1
                polls.append(PollAnswer(f'{matches[int(player)-1][0]} - {matches[int(player)-1][1]}', str(i)))

            await utils.answer_file(message, file=InputMediaPoll(poll=Poll(
                id = random.randint(1, 9999999),
                question=win,
                answers=polls
            )))
        except Exception as e:
            await utils.answer(message, self.strings("no_answers"))
        