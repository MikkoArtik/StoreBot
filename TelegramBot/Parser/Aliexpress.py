from math import inf

from selenium.webdriver import Chrome
from selenium.common.exceptions import NoSuchElementException


PRICE_CLASS_NAME = 'product-price-value'


def get_src_price(browser: Chrome) -> str:
    try:
        return browser.find_element_by_class_name(PRICE_CLASS_NAME).text
    except NoSuchElementException:
        return ''


def get_float_price(src_line: str) -> float:
    value = [x for x in src_line if x.isdigit() or x in ('.', ',')]
    value = ''.join(value).replace(',', '.')
    if value[-1] == '.':
        value = value[:-1]
    try:
        value = float(value)
    except ValueError:
        value = inf
    return value


def get_float_minimal_price(src_line: str) -> float:
    src_line = src_line.replace(' ', '')
    low = src_line.split('-')[0]
    low = get_float_price(low)
    return low


def get_price(browser: Chrome, link: str) -> float:
    browser.get(link)
    src_price = get_src_price(browser)
    current_price = get_float_minimal_price(src_price)
    return current_price
