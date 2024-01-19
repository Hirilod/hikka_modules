# ---------------------------------------------------------------------------------
# Name: Chat GPT
# Author: @hirilod
# ---------------------------------------------------------------------------------
# 🔒    Licensed under the GNU AGPLv3
# 🌐 https://www.gnu.org/licenses/agpl-3.0.html

# meta developer: @hirilod
# requires: openai, tempfile
# ---------------------------------------------------------------------------------




from telethon.tl.types import Message

from . import loader, utils
import asyncio
from openai import AsyncOpenAI
@loader.tds
class GPT(loader.Module):
    '''ChatGPT API '''
    strings = {
        'name': 'Chat GPT',
        'gpt3': '[вопрос] - отправить вопрос GPT-3.5-Turbo',
        'gpt4': '[вопрос] - отправить вопрос GPT-3.5-Turbo',
        "no_args": (
            "<b>Не указаны"
            " аргументы</b>"
        ),
        "no_api_key": (
            "<b>API ключ не указан</b>"
        ),
    }
    
    def __init__(self): 
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                'gpt_token',
                '',
                'API ключ Open AI',
                validator=loader.validators.Hidden()
            ),
            loader.ConfigValue(
                'gpt_proxy',
                '',
                'HTTP Proxy для запроса(если сервер находится в России)',
                validator=loader.validators.Link()
            )
        )
    
    async def _get_char(self, message: str):
        
    
    @loader.command(ru_doc='[вопрос] - отправить вопрос GPT-3.5-Turbo', en_doc='[question] - send a question to GPT-3.5-Turbo')
    async def gpt3(self, message: Message):
        if self.config["gpt_token"] == "":
            return await utils.answer(message, self.strings("no_api_key"))
        args = utils.get_args_raw(message)
        if not args:
            return await utils.answer(message, self.strings("no_args"))
        
        await utils.answer(
            message,
            "Генерирует ответ...",
            )
        