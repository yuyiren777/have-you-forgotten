"""数据库连接管理"""
import os
import shutil
import sys
from peewee import SqliteDatabase

# 数据目录
def _get_data_dir() -> str:
    """Keep packaged-app data outside the install directory."""
    if getattr(sys, "frozen", False):
        local_app_data = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return os.path.join(local_app_data, "HaveYouForgotten")
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def _migrate_legacy_data(target_dir: str):
    """Copy existing packaged-version data before its old folder is removed."""
    if not getattr(sys, "frozen", False) or os.path.exists(os.path.join(target_dir, "app.db")):
        return

    legacy_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    if not os.path.isdir(legacy_dir):
        return

    os.makedirs(target_dir, exist_ok=True)
    for name in ("app.db", "app.db-wal", "app.db-shm"):
        source = os.path.join(legacy_dir, name)
        if os.path.isfile(source):
            shutil.copy2(source, os.path.join(target_dir, name))

    legacy_images = os.path.join(legacy_dir, "images")
    if os.path.isdir(legacy_images):
        shutil.copytree(legacy_images, os.path.join(target_dir, "images"), dirs_exist_ok=True)


DATA_DIR = _get_data_dir()
_migrate_legacy_data(DATA_DIR)
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, 'images'), exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, 'app.db')

db = SqliteDatabase(DB_PATH, pragmas={
    'journal_mode': 'wal',
    'foreign_keys': 1,
    'busy_timeout': 5000,
    'synchronous': 1,
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
