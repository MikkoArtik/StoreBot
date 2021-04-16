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
        self.__orm: Orm = None
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
    def orm(self) -> Orm:
        if self.__orm is not None:
            return self.__orm

        class BaseModel(Model):
            class Meta:
                database = self.db

        class Info(BaseModel):
            id = PrimaryKeyField(null=False)
            chat_id = IntegerField(null=False)
            dt_val = DateTimeField(null=False)
            store = CharField(null=False)
            link = CharField(null=False)
            price = FloatField(null=False)
            status = BooleanField(default=ACTIVE_STATUS)

            class Meta:
                db_table = 'Info'

        self.__orm = Orm(Info)
        return self.__orm

    def create_db(self):
        tabs = [self.orm.info]
        self.db.create_tables(tabs, safe=True)

    def add_record(self, rec: Record):
        table = self.orm.info
        row = table(chat_id=rec.chat_id, dt_val=rec.dt, store=rec.store,
                    link=rec.link, price=rec.price)
        row.save()

    def records_count(self, chat_id: int) -> int:
        table = self.orm.info
        return table.select().where((table.chat_id == chat_id) & (table.status == ACTIVE_STATUS)).count()

    def get_active_records(self) -> list:
        table = self.orm.info
        result = []
        for rec in table.select().where(table.status == ACTIVE_STATUS):
            result.append((rec.id, rec.chat_id, rec.store, rec.link,
                           rec.price))
        return result

    def change_record_status(self, id_val: int, status):
        table = self.orm.info
        rec = table.select().where(table.id == id_val).get()
        rec.status = status
        rec.save()

    def clearing_db(self):
        current_dt = datetime.now()
        table = self.orm.info
        for rec in table.select():
            delta_days = (current_dt - rec.dt_val).days
            if delta_days > MAXIMAL_DAYS:
                rec.status = DELETED_STATUS
                rec.save()
