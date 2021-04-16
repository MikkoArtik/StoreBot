import re
from typing import NamedTuple
from datetime import datetime
import logging


from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from TelegramBot.DBase.DBase import DBase

from TelegramBot.DBase.DBase import MAXIMAL_DAYS, MAXIMAL_REC_COUNT


STORES = ['Aliexpress']
COMMANDS = ['start', 'add']


class UserData(StatesGroup):
    store_name = State()
    link = State()
    price = State()


class Record(NamedTuple):
    chat_id: int
    dt: datetime
    store: str
    link: str
    price: str


def link_message_clearing(src_text: str) -> str:
    try:
        url = re.search("(?P<url>https?://[^\s]+)", src_text).group("url")
    except AttributeError:
        url = ''
    url = url.replace('m.aliexpress', 'aliexpress')
    return url


class BotCore:
    def __init__(self, token):
        self.__db = None
        self.__token = token
        self.__bot = None

    @property
    def token(self) -> str:
        return self.__token

    @property
    def db(self) -> DBase:
        if self.__db is None:
            self.__db = DBase()
        return self.__db

    @property
    def bot(self) -> Bot:
        if self.__bot is None:
            self.__bot = Bot(self.token)
        return self.__bot

    @staticmethod
    async def start_bot(message: types.Message):
        user_name = message.from_user.first_name
        await message.answer(f'Привет, {user_name}! Я помогу купить '
                             f'нужную вещь по приемлемой для тебя цене. '
                             f'Выбирай нужный магазин, бросай ссылку и цену,'
                             f' а я оповещу тебя, как только цена достигнет '
                             f'нужного уровня')

        await message.answer('Команды бота:\n/add - добавить новую ссылку для '
                             'отслеживания цены;\n'
                             '/cancel - отмена операции')

    async def add_command(self, message: types.Message, state: FSMContext):
        await state.finish()

        user_id = message.from_user.id
        rec_count = self.db.records_count(user_id)
        if rec_count >= MAXIMAL_REC_COUNT:
            await message.answer('Ты уже отслеживаешь достаточно ссылок')
            return
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(*STORES)
        await message.answer('Выбирай магазин', reply_markup=keyboard)
        await UserData.store_name.set()

    @staticmethod
    async def cancel_command(message: types.Message, state: FSMContext):
        await state.finish()
        await message.answer('Действие отменено',
                             reply_markup=types.ReplyKeyboardRemove())

    @staticmethod
    async def store_chosen(message: types.Message, state: FSMContext):
        if message.text not in STORES:
            await message.answer('Выбери магазин, используя клавиатуру')
            return
        await state.update_data(store=message.text)
        await message.answer('Теперь присылай ссылку на товар',
                             reply_markup=types.ReplyKeyboardRemove())
        await UserData.next()

    @staticmethod
    async def link_added(message: types.Message, state: FSMContext):
        data = await state.get_data()
        store = data['store']

        url = link_message_clearing(message.text)
        if store.lower() not in url.lower():
            await message.answer('Некорректная ссылка. Попробуй еще раз')
            return
        await state.update_data(link=url)
        await message.answer('За какую цену хочешь купить? '
                             '(Разделитель дробной части - точка)')
        await UserData.next()

    async def price_added(self, message: types.Message, state: FSMContext):
        try:
            price = float(message.text)
        except ValueError:
            await message.answer('Некорректно введена цена. Попробуй еще раз')
            return
        await state.update_data(price=price)
        await message.answer(f'Отлично! Как только цена достигнет нужного '
                             'уровня,я обязательно об этом сообщу! Отслеживать '
                             f'буду в течение {MAXIMAL_DAYS} дней. Если хочешь '
                             'еще что-то добавить - кликай: /add')
        data = await state.get_data()
        chat_id = message.chat.id
        dt = datetime.now()

        rec = Record(chat_id, dt, data["store"], data["link"], data["price"])

        self.db.add_record(rec)
        await state.finish()

    def register_handlers(self, dp: Dispatcher):
        dp.register_message_handler(self.start_bot, commands='start')
        dp.register_message_handler(self.add_command, commands='add', state='*')
        dp.register_message_handler(self.cancel_command, commands='cancel', state='*')
        dp.register_message_handler(self.store_chosen, state=UserData.store_name)
        dp.register_message_handler(self.link_added, state=UserData.link)
        dp.register_message_handler(self.price_added, state=UserData.price)

    def starting(self):
        dp = Dispatcher(self.bot, storage=MemoryStorage())
        logging.basicConfig(level=logging.INFO)
        self.register_handlers(dp)
        executor.start_polling(dp, skip_updates=True)
