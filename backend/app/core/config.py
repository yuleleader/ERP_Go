# -*- coding: utf-8 -*-
import os
import secrets
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

# SECRET_KEY 支持通过环境变量注入；未设置时自动生成随机密钥并持久化到本地文件，
# 不再使用公开默认值（公开默认值可被用来伪造任意角色 JWT）。
os.makedirs(DATA_DIR, exist_ok=True)
_env_key = os.environ.get("SECRET_KEY")
if _env_key:
    SECRET_KEY = _env_key
else:
    _key_file = DATA_DIR / ".secret_key"
    if _key_file.exists():
        SECRET_KEY = _key_file.read_text(encoding="utf-8").strip() or secrets.token_hex(32)
    else:
        SECRET_KEY = secrets.token_hex(32)
        try:
            _key_file.write_text(SECRET_KEY, encoding="utf-8")
        except OSError:
            pass  # 写入失败时至少本次进程内为随机密钥
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
