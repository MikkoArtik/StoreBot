import os
from datetime import datetime
from time import sleep
import imp
from threading import Thread

import requests

from selenium.webdriver import ChromeOptions
from selenium.webdriver import Chrome

from TelegramBot import DBase
from TelegramBot.DBase.DBase import DELETED_STATUS
from TelegramBot.DBase.DBase import INFINITY_PRICE

from TelegramBot import Parser


PRICE_CHECKING_HOURS = [11, 17]
DB_CLEARING_HOURS = [1]
URL_PATTERN = 'https://api.telegram.org/bot{token}/{method}'
SEND_MESSAGE = 'sendMessage'
MIN_PERCENT_DETECTION = 2


def get_driver_path():
    module_folder = imp.find_module('TelegramBot')[1]
    return os.path.join(module_folder, 'Core', 'chromedriver')


class Monitoring:
    def __init__(self, token):
        self.__token = token
        self.__db = None

    @property
    def token(self) -> str:
        return self.__token

    @property
    def db(self) -> DBase:
        if self.__db is None:
            self.__db = DBase()
        return self.__db

    @property
    def browser(self) -> Chrome:
        options = ChromeOptions()
        options.add_argument('headless')
        options.add_argument('window-size=1200x600')
        return Chrome(executable_path=get_driver_path(), options=options)

    def send_message_by_chat_id(self, chat_id: int, message: str) -> bool:
        url = URL_PATTERN.format(token=self.token, method=SEND_MESSAGE)
        req = requests.post(url=url, data={'chat_id': chat_id,
                                           'text': message,
                                           'parse_mode': 'markdown'})
        return req.json()['ok']

    def clearing_dbase(self):
        while True:
            current_time = datetime.now().time()
            if current_time.hour in DB_CLEARING_HOURS:
                self.db.clearing_db()
            sleep(60 * 60)

    def notify_sending(self):
        while True:
            current_hour = datetime.now().time().hour
            if current_hour in PRICE_CHECKING_HOURS:
                browser = self.browser
                for rec in self.db.get_active_records():
                    rec_id, chat_id, store, link, target_price, last_price = rec
                    browser.get(link)
                    current_price = Parser(browser, store).get_minimal_price()
                    if current_price == INFINITY_PRICE:
                        continue

                    self.db.change_prices_by_id(rec_id, current_price)
                    if current_price <= target_price:
                        message = f'Цена товара по ссылке [{store}]({link})\n' \
                                  f'достигла цели - {current_price}'
                        self.send_message_by_chat_id(chat_id, message)
                        self.db.change_record_status(rec_id, DELETED_STATUS)
                        continue

                    if last_price == INFINITY_PRICE:
                        continue

                    price_delta = current_price - last_price
                    percent = int(round(price_delta / last_price * 100))
                    if abs(percent) < MIN_PERCENT_DETECTION:
                        continue

                    if percent < 0:
                        message = f'Цена товара по ссылке [{store}]({link})\n' \
                                  f'снизилась на {abs(percent)}%. Ждем ' \
                                  f'падения дальше)'
                    else:
                        message = f'Цена товара по ссылке [{store}]({link})\n' \
                                  f'повысилась на {abs(percent)}%. Может ' \
                                  f'купить, пока не стало еще дороже?'

                    self.send_message_by_chat_id(chat_id, message)
                browser.close()
            sleep(60 * 60)


class ClearingThread(Thread):
    def __init__(self, token: str):
        self.token = token
        Thread.__init__(self)

    def run(self):
        Monitoring(self.token).clearing_dbase()


class UserNotifyingThread(Thread):
    def __init__(self, token: str):
        self.token = token
        Thread.__init__(self)

    def run(self):
        Monitoring(self.token).notify_sending()
