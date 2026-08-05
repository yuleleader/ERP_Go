# -*- coding: utf-8 -*-
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Date, Numeric
from sqlalchemy.sql import func
from sqlalchemy import event
from datetime import datetime as dt, timezone, timedelta
from ..core.database import Base

CST = timezone(timedelta(hours=8))

def now_cst():
    """返回当前北京时间（带时区，aware）"""
    return dt.now(CST)

def beijing_now():
    """返回当前北京时间（naive，明确北京时间语义，不依赖服务器时区）"""
    return dt.now(CST).replace(tzinfo=None)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    real_name = Column(String(100), nullable=True)
    role = Column(String(20), nullable=False, default="sales")
    commission_rate = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'))
    updated_at = Column(DateTime, server_default=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'), onupdate=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'))

class Shop(Base):
    __tablename__ = "shops"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    shop_id = Column(String(100), unique=True, index=True, nullable=False)
    shop_name = Column(String(100), nullable=False)      # 业务规则：同邮箱可在不同平台注册，唯一性为"名称+账号"组合
    shop_account = Column(String(100), nullable=False)   # 通常为邮箱；不再全局唯一
    status = Column(String(20), default="normal")
    creator = Column(String(50), nullable=False)
    create_time = Column(DateTime, server_default=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'))
    update_time = Column(DateTime, server_default=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'), onupdate=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'))

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_id = Column(String(100), unique=True, index=True, nullable=False)
    shop_id = Column(String(100), nullable=True)
    product_name = Column(String(255), nullable=True)
    platform_order_no = Column(String(100), unique=True, nullable=False)
    sales_amount = Column(String(20), nullable=True)
    shipping_status = Column(String(20), default="pending")
    logistics_company = Column(String(100), nullable=True)
    logistics_no = Column(String(100), nullable=True)
    logistics_no_2 = Column(String(100), nullable=True)  # 运单号2（选填，发货端维护）
    freight = Column(String(20), nullable=True)  # 运费：仅老板端可编辑、发货端可填写，销售端/工厂端只读
    shipping_operator = Column(String(50), nullable=True)
    shipping_time = Column(DateTime, nullable=True)
    receiver_address = Column(Text, nullable=True)
    detected_country = Column(String(100), nullable=True, index=True)  # 离线/翻译/搜索识别出的国家中文名；NULL=未计算, ""=识别不到
    remark = Column(Text, nullable=True)
    commission_rate = Column(Integer, nullable=True)
    commission_amount = Column(String(20), nullable=True)
    created_by = Column(String(50), nullable=True)
    created_at = Column(DateTime, server_default=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'))
    order_days = Column(Integer, default=0, nullable=True)
    commission_paid = Column(Boolean, default=False, nullable=False)
    produce_status = Column(String(20), default="unproduce", nullable=False)
    produce_status_update_at = Column(DateTime, nullable=True)
    produce_status_update_user = Column(String(50), nullable=True)
    updated_at = Column(DateTime, server_default=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'), onupdate=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'))

class Image(Base):
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_id = Column(String(100), index=True, nullable=True)
    temp_id = Column(String(100), nullable=True)
    image_type = Column(String(50), nullable=True)
    image_url = Column(String(500), nullable=True)
    thumbnail_url = Column(String(500), nullable=True)
    image_hash = Column(String(64), nullable=True)
    is_main = Column(Integer, default=0)
    uploaded_by = Column(String(50), nullable=True)
    is_locked = Column(Integer, default=0)
    layer = Column(String(20), nullable=True, default="sales")
    created_at = Column(DateTime, server_default=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'))
    updated_at = Column(DateTime, server_default=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'), onupdate=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'))

class OperationLog(Base):
    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, nullable=True)
    username = Column(String(50), nullable=True)
    operation_type = Column(String(50), nullable=False)
    operation_content = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'))

class LoginLog(Base):
    __tablename__ = "login_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), nullable=False)
    login_time = Column(DateTime, server_default=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'))
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)
    status = Column(String(20), default="success")

class SystemSetting(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=True)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'))
    updated_at = Column(DateTime, server_default=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'), onupdate=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'))

class LogisticsCompany(Base):
    __tablename__ = "logistics_companies"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    company_code = Column(String(50), unique=True, nullable=False)
    company_name = Column(String(100), unique=True, nullable=False)
    contact_person = Column(String(50), nullable=True)
    contact_phone = Column(String(20), nullable=True)
    status = Column(String(20), default="active")
    created_by = Column(String(50), nullable=True)
    created_at = Column(DateTime, server_default=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'))
    updated_at = Column(DateTime, server_default=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'), onupdate=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'))

class LogCleanupRecord(Base):
    __tablename__ = "log_cleanup_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cleanup_type = Column(String(50), nullable=False)
    retention_days = Column(Integer, nullable=False)
    deleted_count = Column(Integer, default=0)
    status = Column(String(20), default="pending")
    error_message = Column(Text, nullable=True)
    start_time = Column(DateTime, server_default=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'))
    end_time = Column(DateTime, nullable=True)
    triggered_by = Column(String(50), nullable=True)
    operator_username = Column(String(50), nullable=True)

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    recipient_username = Column(String(50), nullable=False, index=True)
    order_id = Column(String(100), nullable=True, index=True)
    event_type = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'))

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_code = Column(String(50), unique=True, index=True, nullable=False)
    product_name = Column(String(100), nullable=False)
    product_remark = Column(Text, nullable=True)
    status = Column(String(20), default="active")
    created_by = Column(String(50), nullable=True)
    created_at = Column(DateTime, server_default=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'))
    updated_at = Column(DateTime, server_default=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'), onupdate=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'))

class ShopWithdrawRecord(Base):
    __tablename__ = "shop_withdraw_record"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    shop_id = Column(String(64), nullable=False, index=True)
    withdraw_date = Column(String(20), nullable=False, index=True)
    withdraw_amount = Column(String(20), nullable=False)
    remark = Column(String(500), nullable=True)
    create_operator_name = Column(String(50), nullable=False)
    create_operator_id = Column(Integer, nullable=False)
    update_operator_name = Column(String(50), nullable=True)
    update_operator_id = Column(Integer, nullable=True)
    create_time = Column(DateTime, server_default=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'))
    update_time = Column(DateTime, server_default=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'), onupdate=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'))

@event.listens_for(User, 'before_insert')
@event.listens_for(Shop, 'before_insert')
@event.listens_for(Order, 'before_insert')
@event.listens_for(Image, 'before_insert')
@event.listens_for(OperationLog, 'before_insert')
@event.listens_for(LoginLog, 'before_insert')
@event.listens_for(SystemSetting, 'before_insert')
@event.listens_for(LogisticsCompany, 'before_insert')
@event.listens_for(LogCleanupRecord, 'before_insert')
@event.listens_for(Notification, 'before_insert')
@event.listens_for(Product, 'before_insert')
@event.listens_for(ShopWithdrawRecord, 'before_insert')
def set_create_time_before_insert(mapper, connection, target):
    for col in ['created_at', 'create_time', 'login_time', 'start_time', 'updated_at', 'update_time']:
        if hasattr(target, col) and getattr(target, col) is None:
            setattr(target, col, now_cst())

@event.listens_for(User, 'before_update')
@event.listens_for(Shop, 'before_update')
@event.listens_for(Order, 'before_update')
@event.listens_for(Image, 'before_update')
@event.listens_for(SystemSetting, 'before_update')
@event.listens_for(LogisticsCompany, 'before_update')
@event.listens_for(Product, 'before_update')
@event.listens_for(ShopWithdrawRecord, 'before_update')
def set_update_time_before_update(mapper, connection, target):
    for col in ['updated_at', 'update_time']:
        if hasattr(target, col):
            setattr(target, col, now_cst())