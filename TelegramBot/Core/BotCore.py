import re
import hashlib
from datetime import datetime
import logging

from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from TelegramBot import DBase
from TelegramBot.DBase.DBase import LINK_LIFE_DAYS, BASE_MAXIMAL_REC_COUNT
from TelegramBot.DBase.DBase import BASE_ACCOUNT, PRO_ACCOUNT


ALI_STORE = 'AliExpress'
WILDBERRIES_STORE = 'Wildberries'
OZON_STORE = 'Ozon'
STORES = [ALI_STORE, WILDBERRIES_STORE]


class UserData(StatesGroup):
    store_name = State()
    link = State()
    price = State()


class Activation(StatesGroup):
    key_added = State()


def check_link_conformity(link: str, store: str):
    if store.lower() in link.lower():
        return True


def link_message_clearing(src_text: str) -> str:
    try:
        url = re.search("(?P<url>https?://[^\s]+)", src_text).group("url")
    except AttributeError:
        url = ''
    url = url.replace('m.aliexpress', 'aliexpress')
    return url


def get_key(user_name: str) -> str:
    current_date = datetime.now().date().strftime('%d-%m-%Y')
    code_line = 'Orion' + current_date + user_name
    code_line = code_line.encode('utf-8')
    return hashlib.sha1(code_line).hexdigest()


def is_valid_key(user_name: str, key_val: str) -> bool:
    if key_val == get_key(user_name):
        return True
    return False


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
                             f'нужного уровня или станет еще ниже')

        await message.answer('Команды бота:\n'
                             '/add - добавить новую ссылку для '
                             'отслеживания цены;'
                             '\n/cancel - отмена операции')

    async def add_command(self, message: types.Message, state: FSMContext):
        await state.finish()
        user_id, chat_id = message.from_user.username, message.chat.id
        self.db.add_user(chat_id=chat_id)
        account_type = self.db.get_account_type_by_chat_id(chat_id)
        rec_count = self.db.records_count(chat_id)
        if rec_count >= BASE_MAXIMAL_REC_COUNT and account_type == BASE_ACCOUNT:
            await message.answer('Сейчас у тебя базовый аккаунт, который '
                                 'позволяет отслеживать не более '
                                 f'{BASE_MAXIMAL_REC_COUNT} ссылок. Ты уже '
                                 'отслеживаешь максимальное их количество. '
                                 'Если хочешь получить расширенные '
                                 'возможности - напиши @Mikko92')
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
        if not check_link_conformity(url, store):
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
                             'уровня, я обязательно об этом сообщу! '
                             f'Отслеживать буду в течение {LINK_LIFE_DAYS} '
                             f'дней. Если хочешь еще что-то добавить - '
                             f'кликай: /add')
        data = await state.get_data()
        chat_id = message.chat.id
        self.db.add_link(chat_id=chat_id, store=data['store'],
                         link=data['link'], target_price=data['price'])
        await state.finish()

    async def account_activation(self, message: types.Message, state: FSMContext):
        await state.finish()
        user_name, chat_id = message.from_user.username, message.chat.id
        self.db.add_user(chat_id=chat_id)
        account_type = self.db.get_account_type_by_chat_id(chat_id)
        if account_type == PRO_ACCOUNT:
            await message.answer('У тебя уже pro-аккаунт. Активация не '
                                 'требуется')
            return
        await message.answer('Жду ключ для активации подписки')
        await Activation.next()

    async def key_added(self, message: types.Message, state: FSMContext):
        user_name = message.from_user.username
        current_key_value = message.text
        if is_valid_key(user_name, current_key_value):
            await message.answer('Отлично! Подписка активирована на 30 дней')
            await state.finish()
            chat_id = message.chat.id
            self.db.change_account_type_by_chat_id(chat_id, PRO_ACCOUNT)
        else:
            await message.answer('Ключ введен неверно. Попробуй еще раз или '
                                 'введи /cancel для отмены')
            return

    def register_handlers(self, dp: Dispatcher):
        dp.register_message_handler(self.start_bot, commands='start')
        dp.register_message_handler(self.add_command, commands='add', state='*')
        dp.register_message_handler(self.cancel_command, commands='cancel', state='*')
        dp.register_message_handler(self.store_chosen, state=UserData.store_name)
        dp.register_message_handler(self.link_added, state=UserData.link)
        dp.register_message_handler(self.price_added, state=UserData.price)
        dp.register_message_handler(self.account_activation, commands='key', state='*')
        dp.register_message_handler(self.key_added, state=Activation.key_added)

    def start(self):
        dp = Dispatcher(self.bot, storage=MemoryStorage())
        logging.basicConfig(level=logging.INFO)
        self.register_handlers(dp)
        executor.start_polling(dp, skip_updates=True)
