from typing import List

from selenium.webdriver import Chrome
from selenium.common.exceptions import NoSuchElementException

from TelegramBot.DBase.DBase import INFINITY_PRICE
from TelegramBot.Core.BotCore import ALI_STORE, WILDBERRIES_STORE, OZON_STORE


class InvalidStoreName(Exception):
    pass


class Parser:
    def __init__(self, browser: Chrome, store: str):
        self.__browser = browser
        if store not in [ALI_STORE, WILDBERRIES_STORE]:
            raise InvalidStoreName
        self.__store = store

    @property
    def browser(self) -> Chrome:
        return self.__browser

    @property
    def store(self) -> str:
        return self.__store

    @property
    def x_paths(self) -> List[str]:
        if self.store == ALI_STORE:
            return ['//span[@class="product-price-value"]']
        elif self.store == WILDBERRIES_STORE:
            return ['//span[@class="final-cost"]']
        elif self.store == OZON_STORE:
            # return ['//span[@class="c2h5"]', '//span[@class="c2h5 c2h6"]']
            return []
        else:
            return []

    def get_src_price(self) -> str:
        for path in self.x_paths:
            try:
                return self.browser.find_element_by_xpath(path).text
            except NoSuchElementException:
                continue
        else:
            return ''

    @staticmethod
    def get_float_price(src_line: str) -> float:
        value = [x for x in src_line if x.isdigit() or x in ('.', ',')]
        try:
            value = ''.join(value).replace(',', '.')
            if value[-1] == '.':
                value = value[:-1]
            value = float(value)
        except (ValueError, IndexError):
            value = INFINITY_PRICE
        return value

    def get_minimal_price(self) -> float:
        src_line = self.get_src_price().replace(' ', '')
        if self.store == ALI_STORE:
            low = src_line.split('-')[0]
            return self.get_float_price(low)
        elif self.store == WILDBERRIES_STORE:
            return self.get_float_price(src_line)
        elif self.store == OZON_STORE:
            return self.get_float_price(src_line)
