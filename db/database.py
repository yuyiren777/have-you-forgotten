"""数据库连接管理"""
import os
from peewee import SqliteDatabase

# 数据目录
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, 'images'), exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, 'app.db')

db = SqliteDatabase(DB_PATH, pragmas={
    'journal_mode': 'wal',
    'foreign_keys': 1,
})


def init_db():
    """初始化数据库，创建所有表"""
    from db.models import Config, Input, Schedule, ReminderLog
    db.connect()
    db.create_tables([Config, Input, Schedule, ReminderLog], safe=True)
    db.close()


def get_db():
    """获取数据库连接"""
    if db.is_closed():
        db.connect()
    return db
