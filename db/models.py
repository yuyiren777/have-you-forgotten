"""数据库模型 (peewee ORM)"""
import datetime
from peewee import (
    Model, AutoField, CharField, TextField, DateField, TimeField,
    DateTimeField, IntegerField, ForeignKeyField
)
from db.database import db


class BaseModel(Model):
    class Meta:
        database = db


class Config(BaseModel):
    """用户配置表"""
    key = CharField(primary_key=True, max_length=64)
    value = TextField()

    class Meta:
        table_name = 'config'


class Input(BaseModel):
    """原始输入表"""
    id = AutoField()
    type = CharField(max_length=16)  # 'text' | 'image'
    content = TextField(null=True)   # 文字内容
    image_path = TextField(null=True)  # 图片本地存储路径
    created_at = DateTimeField(default=datetime.datetime.now)

    class Meta:
        table_name = 'inputs'


class Schedule(BaseModel):
    """日程表（核心）"""
    id = AutoField()
    input = ForeignKeyField(Input, backref='schedules', null=True)
    title = CharField(max_length=512)
    description = TextField(null=True)
    date = DateField(null=True)
    start_time = TimeField(null=True)
    end_time = TimeField(null=True)
    location = CharField(max_length=512, null=True)
    notes = TextField(null=True)
    repeat_rule = CharField(max_length=64, null=True)  # 'daily' | 'weekly:1,3,5' | 'monthly:15' | None
    urgency = IntegerField(default=0)  # 0=普通 1=重要 2=紧急
    status = CharField(max_length=32, default='pending')  # pending | reminded | completed | expired
    reminded_at = DateTimeField(null=True)
    created_at = DateTimeField(default=datetime.datetime.now)
    updated_at = DateTimeField(default=datetime.datetime.now)

    class Meta:
        table_name = 'schedules'

    def to_dict(self):
        return {
            'id': self.id,
            'input_id': self.input_id,
            'title': self.title,
            'description': self.description,
            'date': self.date.isoformat() if self.date else None,
            'start_time': self.start_time.strftime('%H:%M') if self.start_time else None,
            'end_time': self.end_time.strftime('%H:%M') if self.end_time else None,
            'location': self.location,
            'notes': self.notes,
            'repeat_rule': self.repeat_rule,
            'urgency': self.urgency,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def is_overdue(self):
        """判断日程是否已过期"""
        if not self.date:
            return False
        today = datetime.date.today()
        if self.end_time:
            now = datetime.datetime.now().time()
            return self.date < today or (self.date == today and self.end_time < now)
        return self.date < today


class ReminderLog(BaseModel):
    """提醒记录表"""
    id = AutoField()
    schedule = ForeignKeyField(Schedule, backref='reminder_logs')
    method = CharField(max_length=32)  # 'windows' | 'wechat' | 'email'
    status = CharField(max_length=32)  # 'sent' | 'failed' | 'dismissed'
    message = TextField(null=True)
    created_at = DateTimeField(default=datetime.datetime.now)

    class Meta:
        table_name = 'reminder_logs'
