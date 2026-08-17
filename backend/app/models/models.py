# -*- coding: utf-8 -*-
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Date, Numeric, Float
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
    # 价格权限：逗号分隔字符串，如 "cost_price,retail_price,min_price"
    # None/空 = 全部可见（老用户向后兼容）；boss 角色恒可见全部
    price_permissions = Column(String(100), nullable=True)
    data_permissions = Column(Text, nullable=True)  # 数据权限 JSON：{"/orders":["query","export"],"/products":["query","add","edit","delete"]}；兼容旧键 category/brand/product；空=无；boss 恒全权
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
    platform_code = Column(String(10), nullable=True, index=True)  # 历史遗留列（原关联平台编码）；新设计改用 platform_id，本列保留兼容、不再写入读取
    platform_id = Column(Integer, nullable=True, index=True)  # 关联 platforms.id；NULL=手工录入网店（API 逻辑全部不生效）

    # ===== 店铺级 API 配置（platform_id 不为 null 时生效；密钥类字段数据库加密存储） =====
    api_app_key = Column(String(255), nullable=True)            # 店铺私有 AppKey
    api_app_secret = Column(Text, nullable=True)               # 店铺私有密钥（加密存储）
    api_access_token = Column(Text, nullable=True)             # OAuth 访问令牌（加密存储）
    api_refresh_token = Column(Text, nullable=True)            # OAuth 刷新令牌（加密存储）
    api_token_expire = Column(DateTime, nullable=True)         # Token 过期时间（后端自动更新，只读）
    api_auth_scope = Column(Text, nullable=True)               # 授权权限范围（接口返回回填，只读）
    api_self_qps = Column(Integer, default=8, nullable=True)   # 单店最大请求 QPS，默认 8；不能超过平台全局 QPS
    sync_auto_enable = Column(Integer, default=1, nullable=True)    # 自动同步开关 0关闭/1开启，默认 1
    sync_order_interval = Column(Integer, default=5, nullable=True)  # 自动同步间隔（分钟），默认 5
    sync_time_window = Column(Integer, default=1, nullable=True)     # 单次拉取订单时间窗口（小时），默认 1
    last_sync_success_time = Column(DateTime, nullable=True)   # 上次成功同步订单时间（增量拉单核心，后端自动更新，只读）
    api_retry_count = Column(Integer, default=3, nullable=True)      # 接口失败最大重试次数，默认 3
    api_retry_base_ms = Column(Integer, default=1000, nullable=True) # 重试基础间隔毫秒，默认 1000
    webhook_callback = Column(String(500), nullable=True)      # 店铺独立 webhook 回调地址
    webhook_verify_key = Column(String(255), nullable=True)    # webhook 验签密钥（加密存储）
    api_ext_json = Column(Text, nullable=True)                 # JSON 扩展字段（店铺特殊参数）

    create_time = Column(DateTime, server_default=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'))
    update_time = Column(DateTime, server_default=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'), onupdate=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'))


class Platform(Base):
    """电商平台（基础信息-平台管理）。存储平台公开公共 API 配置，**不存放任何 AppKey/Token 等密钥**。
    platform_code：平台唯一编码（语义化，如 aliexpress / alibaba_icbu），用户可填，唯一；
    platform_name：平台中文名，唯一；
    status：0 禁用 / 1 启用。
    仅老板端可查看/新增/编辑（其他角色看不到该菜单）。
    网店(Shop)通过 platform_id 关联本表；platform_id 为 NULL 表示手工录入网店。"""
    __tablename__ = "platforms"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    platform_code = Column(String(50), unique=True, index=True, nullable=False)  # 平台唯一编码（语义化），用户填写，不可重复
    platform_name = Column(String(100), unique=True, nullable=False)             # 平台中文名称（唯一）
    remark = Column(String(255), nullable=True)                                  # 备注
    status = Column(Integer, default=1, nullable=False)                          # 0 禁用 / 1 启用

    # ===== API 对接公共配置字段（来自开放平台文档；密钥不在此表） =====
    api_gateway = Column(String(255), nullable=True)            # API 网关地址
    api_version = Column(String(50), nullable=True)            # 接口版本 v3 / top2.0
    api_global_max_qps = Column(Integer, default=10, nullable=True)        # 平台官方全局 QPS 上限
    top_sign_type = Column(String(50), nullable=True)          # TOP 阿里专属：签名算法 hmac-sha1（非阿里平台留空）
    top_default_fields = Column(String(500), nullable=True)    # TOP 阿里专属：订单默认查询字段
    rest_auth_header = Column(String(100), nullable=True)      # REST 通用：鉴权 Header 名
    rest_token_prefix = Column(String(50), nullable=True)      # REST 通用：Token 前缀 Bearer
    webhook_encrypt_type = Column(String(50), nullable=True)  # Webhook：加密方式 sha256

    created_at = Column(DateTime, server_default=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'))
    updated_at = Column(DateTime, server_default=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'), onupdate=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'))

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
    refund_note = Column(Text, nullable=True)  # 退款备注（仅已退货/退款订单，编辑时必填；与 remark 为两个独立字段）
    commission_rate = Column(Integer, nullable=True)
    commission_amount = Column(String(20), nullable=True)
    created_by = Column(String(50), nullable=True)
    created_at = Column(DateTime, server_default=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'))
    order_days = Column(Integer, default=0, nullable=True)
    commission_paid = Column(Boolean, default=False, nullable=False)
    produce_status = Column(String(20), default="unproduce", nullable=False)
    produce_status_update_at = Column(DateTime, nullable=True)
    produce_status_update_user = Column(String(50), nullable=True)
    last_print_at = Column(DateTime, nullable=True)  # 上次打印时间（任一端点过打印按钮即更新）
    gross_profit = Column(Float, nullable=True)  # 毛利 = 销售金额 - 商品成本价（内部统计字段，不在订单界面展示）
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
    category_id = Column(Integer, nullable=True, index=True)   # 关联类别表 id
    brand_id = Column(Integer, nullable=True, index=True)       # 关联品牌表 id
    cost_price = Column(Float, nullable=True)                    # 成本价
    retail_price = Column(Float, nullable=True)                  # 零售价
    min_price = Column(Float, nullable=True)                     # 最低售价
    remark1 = Column(String(500), nullable=True)                 # 备注 1
    remark2 = Column(String(500), nullable=True)                 # 备注 2
    remark3 = Column(String(500), nullable=True)                 # 备注 3
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


class Category(Base):
    """商品类别（基础信息-类别管理），支持两级：一级 002，二级 002001"""
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    category_code = Column(String(20), unique=True, index=True, nullable=False)  # 一级三位(002)，二级六位(002001)
    category_name = Column(String(100), nullable=False)                          # 用户填写
    parent_id = Column(Integer, nullable=True, index=True)                       # 上级类别 id，为空表示一级
    level = Column(Integer, nullable=False, default=1)                           # 1=一级 2=二级
    created_by = Column(String(50), nullable=True)
    created_at = Column(DateTime, server_default=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'))
    updated_at = Column(DateTime, server_default=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'), onupdate=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'))


class Brand(Base):
    """商品品牌（基础信息-品牌管理）"""
    __tablename__ = "brands"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    brand_code = Column(Integer, unique=True, index=True, nullable=False)    # 三位数字，自增（=id）
    brand_name = Column(String(100), nullable=False)                         # 用户填写
    created_by = Column(String(50), nullable=True)
    created_at = Column(DateTime, server_default=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'))
    updated_at = Column(DateTime, server_default=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'), onupdate=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'))


class ProductImage(Base):
    """商品图片（每条对应一张图）。同一 product_code 下最多 5 张，由后端上传接口校验。
    文件存储路径：backend/data/images/product/{product_code}/{uuid}.{ext}
    访问 URL：/data/images/product/{product_code}/{filename}（走 images.serve_router 鉴权）"""
    __tablename__ = "product_images"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_code = Column(String(50), nullable=False, index=True)
    image_url = Column(String(500), nullable=False)               # 完整可访问路径
    file_name = Column(String(255), nullable=True)                # 实际磁盘文件名
    sort_order = Column(Integer, default=0)                       # 排序（上传时间顺序即可）
    uploaded_by = Column(String(50), nullable=True)
    created_at = Column(DateTime, server_default=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'))


class OrderImport(Base):
    """订单批量导入临时表：Excel 上传后先落临时表（按批次 batch_no 分组），
    用户在"数据导入"页逐行查看异常提示 → 编辑修正 → 勾选审核 → 合并进正式 orders 表（生成追溯码）。
    - status: pending=待审核（默认），merged=已合并（合并成功后删除记录，仅审计兜底）
    - errors: JSON 数组字符串，如 ["已发货但生产未完成","退款备注不能为空"]；空数组/空串=无异常
    - sales_amount/freight 存字符串，与正式 orders 表一致（合并时原样带入）
    """
    __tablename__ = "order_imports"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    batch_no = Column(String(40), index=True, nullable=False)     # 导入批次号，同批同号
    platform_order_no = Column(String(100), index=True, nullable=False)
    shop_name = Column(String(100), nullable=True)                # 模板填写的网店名称（用于定位网店）
    shop_account = Column(String(100), nullable=True)             # 模板填写的网店账号（用于定位网店）
    shop_id = Column(String(100), nullable=True)                  # 解析定位到的正式网店 shop_id；None=未匹配成功
    product_name = Column(String(255), nullable=True)
    sales_amount = Column(String(20), nullable=True)
    freight = Column(String(20), nullable=True)
    shipping_status = Column(String(20), default="pending")       # 英文枚举：pending/shipped/virtual/refunded
    produce_status = Column(String(20), default="unproduce")      # 英文枚举：unproduce/producing/produced
    logistics_company = Column(String(100), nullable=True)
    logistics_no = Column(String(100), nullable=True)
    receiver_address = Column(Text, nullable=True)
    remark = Column(Text, nullable=True)
    refund_note = Column(Text, nullable=True)
    order_time = Column(String(30), nullable=True)                # 下单时间（规范化字符串；格式错误时保留原始值并标记异常）
    shipping_time = Column(String(30), nullable=True)             # 发货时间（可选列，用于时间顺序校验）
    errors = Column(Text, nullable=True)                          # JSON 数组字符串
    imported_by = Column(String(50), nullable=False, index=True)  # 导入人 username（合并时作为订单 created_by）
    import_time = Column(DateTime, server_default=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'))
    status = Column(String(20), default="pending")                # pending=待审核 / merged=已合并
    merged_order_id = Column(String(100), nullable=True)          # 合并后生成的正式追溯码
    merged_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, server_default=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'), onupdate=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'))


class AccountingCode(Base):
    """账务代码（财务模块-非交易收支的类型字典）。
    code_type: income=非交易收入 / expense=非交易支出（如买水、广告、佣金等）。
    仅老板端可维护；非交易收支录入时下拉选择。"""
    __tablename__ = "accounting_codes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    code = Column(String(20), unique=True, index=True, nullable=False)   # 自动生成：收入 SR001 / 支出 ZC001（递增）
    name = Column(String(100), nullable=False)                           # 名称：买水/广告/佣金等
    code_type = Column(String(20), nullable=False, default="expense")    # income=非交易收入 / expense=非交易支出
    remark = Column(String(255), nullable=True)                          # 备注
    created_by = Column(String(50), nullable=True)                       # 创建人 username（老板）
    created_at = Column(DateTime, server_default=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'))
    updated_at = Column(DateTime, server_default=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'), onupdate=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'))


class NonTradeTransaction(Base):
    """非交易收入/支出流水（财务模块，每人维护自己的数据）。
    字段：账务代码(code_id) + 关联自己创建的网店(shop_id 可选) + 收入/支出 + 金额 + 备注。
    trans_type: income=收入 / expense=支出（与账务代码类型独立，录入时手动选择）。"""
    __tablename__ = "non_trade_transactions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    code_id = Column(Integer, nullable=False, index=True)               # 关联 accounting_codes.id
    shop_id = Column(String(100), nullable=True, index=True)            # 关联网店（可选，仅限自己创建的网店）
    trans_type = Column(String(20), nullable=False, default="expense")  # income=收入 / expense=支出
    amount = Column(Float, nullable=False, default=0)                   # 金额（>=0）
    remark = Column(String(500), nullable=True)                         # 备注
    created_by = Column(String(50), nullable=False, index=True)         # 录入人 username（每人只能维护自己的）
    create_time = Column(DateTime, server_default=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'))
    update_by = Column(String(50), nullable=True)                       # 最近修改人
    updated_at = Column(DateTime, server_default=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'), onupdate=func.strftime('%Y-%m-%d %H:%M:%S', 'now', '+08:00'))


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
@event.listens_for(Category, 'before_insert')
@event.listens_for(Brand, 'before_insert')
@event.listens_for(ProductImage, 'before_insert')
@event.listens_for(OrderImport, 'before_insert')
@event.listens_for(AccountingCode, 'before_insert')
@event.listens_for(NonTradeTransaction, 'before_insert')
@event.listens_for(Platform, 'before_insert')
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
@event.listens_for(Category, 'before_update')
@event.listens_for(Brand, 'before_update')
@event.listens_for(ProductImage, 'before_update')
@event.listens_for(OrderImport, 'before_update')
@event.listens_for(AccountingCode, 'before_update')
@event.listens_for(NonTradeTransaction, 'before_update')
@event.listens_for(Platform, 'before_update')
def set_update_time_before_update(mapper, connection, target):
    for col in ['updated_at', 'update_time']:
        if hasattr(target, col):
            setattr(target, col, now_cst())