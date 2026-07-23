# -*- coding: utf-8 -*-
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DB_DIR = DATA_DIR / "db"
IMAGES_DIR = DATA_DIR / "images"
TEMP_DIR = IMAGES_DIR / "temp"
OFFICIAL_DIR = IMAGES_DIR / "official"
BACKUP_DIR = DATA_DIR / "backup"
LOGS_DIR = DATA_DIR / "logs"

DB_PATH = DB_DIR / "order_system.db"

DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

SECRET_KEY = "your-secret-key-change-in-production-20260424"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

TEMP_IMAGE_RETENTION_HOURS = 24
QR_CODE_SIZE = 300
QR_CODE_CACHE_DIR = DATA_DIR / "qr_codes"

os.makedirs(DB_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(OFFICIAL_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(QR_CODE_CACHE_DIR, exist_ok=True)
