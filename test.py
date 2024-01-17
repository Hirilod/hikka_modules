from telethon.tl.types import Message
from .. import loader, utils

@loader.tds
class Test(loader.Module):
    strings = {
        'name': 'Test',
        'test': 'Выводит тестовое сообщение'
    }
    
    
    @loader.command(ru_doc='Тест', en_doc='Test')
    async def test_comm(self, message: Message):
        await utils.answer(message, self.strings('test'))