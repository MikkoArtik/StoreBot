import os
from datetime import datetime
from typing import NamedTuple

from peewee import *


MAXIMAL_REC_COUNT = 5
MAXIMAL_DAYS = 30
DB_PATH = '/media/michael/Data/TEMP/example.db'
# DB_PATH = os.path.join(os.getenv('PATH'), 'example.db')

ACTIVE_STATUS = True
DELETED_STATUS = False
ACCOUNT_TYPES = ['base', 'pro']
INFINITY_PRICE = 1e10


class Record(NamedTuple):
    chat_id: int
    dt: datetime
    store: str
    link: str
    price: str


class Orm(NamedTuple):
    info: object


class DBase:
    def __init__(self):
        self.__path = DB_PATH
        self.__db = None
        self.__is_connect = False
        self.__orm = None
        if not os.path.exists(DB_PATH):
            self.create_db()

    @property
    def db(self) -> SqliteDatabase:
        if self.__db is None:
            self.__db = SqliteDatabase(self.__path)
        return self.__db

    @property
    def is_connect(self) -> bool:
        if not self.__is_connect:
            self.__is_connect = self.db.connect()
        return self.__is_connect

    @property
    def orm(self):
        if self.__orm is not None:
            return self.__orm

        class BaseModel(Model):
            class Meta:
                database = self.db

        class User(BaseModel):
            chat_id = IntegerField(null=False)
            reg_date = DateTimeField(null=False, default=datetime.now())
            account_type = CharField(null=False, default='base')

            class Meta:
                db_table = 'Users'

        class Link(BaseModel):
            user = ForeignKeyField(model=User, on_delete='CASCADE')
            store = CharField(null=False)
            link = CharField(null=False)
            reg_dt = DateTimeField(null=False, default=datetime.now())
            target_price = FloatField(default=0)
            pre_price = FloatField(default=INFINITY_PRICE)
            current_price = FloatField(default=INFINITY_PRICE)
            status = BooleanField(default=ACTIVE_STATUS)

            class Meta:
                db_table = 'Links'

        class ORM:
            user: User = User
            link: Link = Link

        return ORM()

    def create_db(self):
        tabs = [self.orm.user, self.orm.link]
        self.db.create_tables(tabs, safe=True)

    def add_user(self, chat_id: int):
        t = self.orm.user
        if t.select().where(t.chat_id == chat_id).count() == 0:
            self.orm.user(chat_id=chat_id).save()

    def add_link(self, chat_id: int, store: str, link: str,
                 target_price=0):
        t = self.orm.user
        user_obj = t.select().where(t.chat_id == chat_id).get()
        t = self.orm.link
        if t.select().where((t.user == user_obj) & (t.link == link)).count() == 0:
            rec = self.orm.link(user=user_obj, store=store, link=link,
                                target_price=target_price)
        else:
            rec = t.select().where((t.user == user_obj) & (t.link == link)).get()
            rec.reg_dt = datetime.now()
            rec.target_price = target_price
        rec.save()

    def records_count(self, chat_id: int) -> int:
        t = self.orm.user
        user_obj = t.select().where(t.chat_id == chat_id).get()
        t = self.orm.link
        return t.select().where((t.user == user_obj) & (t.status == ACTIVE_STATUS)).count()

    def change_record_status(self, id_val: int, status):
        t = self.orm.link
        rec = t.select().where(t.id == id_val).get()
        rec.status = status
        rec.save()

    def clearing_db(self):
        current_dt = datetime.now()
        table = self.orm.link
        for rec in table.select():
            delta_days = (current_dt - rec.reg_dt).days
            if delta_days > MAXIMAL_DAYS:
                rec.status = DELETED_STATUS
                rec.save()

    def get_active_records(self) -> list:
        t = self.orm.link
        result = []
        for rec in t.select().where(t.status == ACTIVE_STATUS):
            result.append((rec.id, rec.user.chat_id, rec.store, rec.link,
                           rec.target_price, rec.current_price))
        return result

    def change_prices_by_id(self, record_id: int, current_price: float):
        t = self.orm.link
        record = t.select().where(t.id == record_id).get()
        if record.pre_price == INFINITY_PRICE:
            record.pre_price = current_price
        else:
            record.pre_price = record.current_price
        record.current_price = current_price
        record.save()
