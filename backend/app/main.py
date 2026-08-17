# -*- coding: utf-8 -*-
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
import os
from sqlalchemy import select
from .core.database import init_db
from .core.config import BASE_DIR, DATA_DIR
from .api import auth, users, shops, orders, images, logs, logistics, statistics, notifications, products, dashboard, commission_settlement, withdraw, categories, brands, settings, product_images, order_imports, warnings, non_trade, platforms, system_backup
from .services.scheduler import setup_scheduler, shutdown_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await create_default_admin()
    await create_default_platforms()
    setup_scheduler(app)
    yield
    shutdown_scheduler()

app = FastAPI(
    title="电商产销协同管理系统",
    description="电商产销协同管理平台API",
    version="1.0.0",
    lifespan=lifespan
)

# ── 全局错误落盘（诊断增强）──
# 原后端异常只经 stdout/stderr 进入启动器图形日志，未落盘，难以事后排查。
# 此处把 uvicorn 的 500 堆栈与根日志同时写入 backend/data/logs/backend_errors.log，
# 便于复现"隔一段时间才出现"的间歇性异常时定位根因。不影响任何接口行为。
import logging
from logging.handlers import RotatingFileHandler

_log_dir = DATA_DIR / "logs"
_log_dir.mkdir(parents=True, exist_ok=True)
_error_file = RotatingFileHandler(
    str(_log_dir / "backend_errors.log"),
    maxBytes=5_000_000,
    backupCount=3,
    encoding="utf-8",
)
_error_file.setLevel(logging.ERROR)
_error_file.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
logging.getLogger("uvicorn.error").addHandler(_error_file)
logging.getLogger().addHandler(_error_file)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(shops.router)
app.include_router(orders.router)
app.include_router(images.router)
app.include_router(logs.router)
app.include_router(logistics.router)
app.include_router(statistics.router)
app.include_router(dashboard.router)
app.include_router(notifications.router)
app.include_router(products.router)
app.include_router(commission_settlement.router)
app.include_router(withdraw.router)
app.include_router(categories.router)
app.include_router(brands.router)
app.include_router(settings.router)
app.include_router(product_images.router)
app.include_router(order_imports.router)
app.include_router(warnings.router)
app.include_router(non_trade.router)
app.include_router(platforms.router)
app.include_router(system_backup.router)

os.makedirs(DATA_DIR / "images", exist_ok=True)
# 图片改为带登录鉴权的路由（?token= / Authorization），关闭免登录静态直链
app.include_router(images.serve_router)

# 手机端作业页：独立轻量页，由后端同源托管在 /m/，复用现有订单/图片 API
MOBILE_DIR = BASE_DIR / "mobile"
if MOBILE_DIR.exists():
    app.mount("/m", StaticFiles(directory=str(MOBILE_DIR), html=True), name="mobile")

@app.get("/m")
async def mobile_root():
    return RedirectResponse("/m/")

@app.get("/")
async def root():
    return {"message": "电商产销协同管理系统 API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

async def create_default_admin():
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import select
    from .core.database import AsyncSessionLocal
    from .core.security import get_password_hash
    from .models.models import User

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.username == "1001"))
        admin = result.scalar_one_or_none()

        if not admin:
            admin = User(
                username="1001",
                password_hash=get_password_hash("1001"),
                real_name="系统管理员",
                role="boss",
                is_active=True
            )
            session.add(admin)
            await session.commit()


async def create_default_platforms():
    """幂等预置 5 个默认电商平台（语义化 code：alibaba_icbu/made_in_china/globalsources/dhgate/aliexpress）并补全真实开放平台 API 配置字段。

    启动即保证存在；新库直接写入完整记录（含真实网关/版本/限流/TOP·REST 字段），
    已存在的库仅补 API 配置字段（不动用户可能改过的名称/状态/备注）；
    用户主动删除某平台后不会自动恢复。
    限流数值为查证到的参考值，实际随账号等级与应用审核变化，接入时按官方文档微调。
    """
    from .core.database import AsyncSessionLocal
    from .models.models import Platform

    defaults = [
        {
            "platform_code": "alibaba_icbu", "platform_name": "阿里巴巴国际站",
            "api_gateway": "https://gw.api.alibaba.com/openapi/",
            "api_version": "2.0",
            "api_global_max_qps": 4,
            "top_sign_type": "hmac-sha1",
            "top_default_fields": "product_id,title,price,sku,moq,logistics",
            "rest_auth_header": "",
            "rest_token_prefix": "",
            "webhook_encrypt_type": "sha256",
            "remark": "阿里系 TOP 开放平台(ICBU)，HMAC-SHA1 签名；仅企业开发者可申请；网关路径含 param2/2.0/<method>",
        },
        {
            "platform_code": "made_in_china", "platform_name": "中国制造网",
            "api_gateway": "https://api.made-in-china.com/",
            "api_version": "2.0",
            "api_global_max_qps": 10,
            "top_sign_type": "",
            "top_default_fields": "",
            "rest_auth_header": "Authorization",
            "rest_token_prefix": "Bearer",
            "webhook_encrypt_type": "sha256",
            "remark": "MIC 开放平台，RESTful + OAuth2.0 + MD5 签名(APIKey+SecretKey+时间戳+随机数)；商品详情 /v2/product/detail",
        },
        {
            "platform_code": "globalsources", "platform_name": "环球资源",
            "api_gateway": "",
            "api_version": "",
            "api_global_max_qps": 10,
            "top_sign_type": "",
            "top_default_fields": "",
            "rest_auth_header": "",
            "rest_token_prefix": "",
            "webhook_encrypt_type": "",
            "remark": "暂无公开标准开放平台API，接入需线下向环球资源申请开发者权限",
        },
        {
            "platform_code": "dhgate", "platform_name": "敦煌网",
            "api_gateway": "http://api.dhgate.com/dop/router",
            "api_version": "1.0",
            "api_global_max_qps": 10,
            "top_sign_type": "",
            "top_default_fields": "",
            "rest_auth_header": "Authorization",
            "rest_token_prefix": "Bearer",
            "webhook_encrypt_type": "sha256",
            "remark": "DOP REST 风格，OAuth2.0 系统参数(method/v/access_token/timestamp)；每分钟≤600次；沙箱 sandbox.api.dhgate.com",
        },
        {
            "platform_code": "aliexpress", "platform_name": "速卖通",
            "api_gateway": "https://openapi.aliexpress.com/router/rest",
            "api_version": "2.0",
            "api_global_max_qps": 5,
            "top_sign_type": "hmac-sha1",
            "top_default_fields": "product_id,title,price,sku,logistics,currency",
            "rest_auth_header": "",
            "rest_token_prefix": "",
            "webhook_encrypt_type": "sha256",
            "remark": "AliExpress Open Platform(阿里系 TOP)，HMAC-SHA1 签名；分区域网关(sg/cn/us)；QPS≤5",
        },
    ]

    # 仅补全的 API 配置字段（存在分支不动名称/状态/备注，尊重用户自定义）
    api_fields = [
        "api_gateway", "api_version", "api_global_max_qps",
        "top_sign_type", "top_default_fields", "rest_auth_header", "rest_token_prefix",
        "webhook_encrypt_type",
    ]

    async with AsyncSessionLocal() as session:
        for d in defaults:
            code = d["platform_code"]
            res = await session.execute(select(Platform).where(Platform.platform_code == code))
            plat = res.scalar_one_or_none()
            if plat is not None:
                # 已存在（按语义编码）：仅补全 API 配置字段，不动名称/状态/备注，尊重用户数据
                for k in api_fields:
                    setattr(plat, k, d[k])
                await session.commit()
                continue
            # 平台名称唯一约束：若已有同名平台（如历史数字编码 01-05 的中文名），
            # 跳过插入，避免 UNIQUE 冲突导致启动失败；现有数据保持不变。
            res2 = await session.execute(select(Platform).where(Platform.platform_name == d["platform_name"]))
            if res2.scalar_one_or_none() is not None:
                continue
            session.add(Platform(
                platform_code=code,
                platform_name=d["platform_name"],
                remark=d["remark"],
                status=1,
                **{k: d[k] for k in api_fields},
            ))
            await session.commit()
