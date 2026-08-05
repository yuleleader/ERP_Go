# -*- coding: utf-8 -*-
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
import os
from .core.database import init_db
from .core.config import BASE_DIR, DATA_DIR
from .api import auth, users, shops, orders, images, logs, logistics, statistics, notifications, products, dashboard, commission_settlement, withdraw
from .services.scheduler import setup_scheduler, shutdown_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await create_default_admin()
    setup_scheduler(app)
    yield
    shutdown_scheduler()

app = FastAPI(
    title="电商产销协同管理系统",
    description="电商产销协同管理平台API",
    version="1.0.0",
    lifespan=lifespan
)

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
