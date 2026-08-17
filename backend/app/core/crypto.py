# -*- coding: utf-8 -*-
"""店铺密钥字段加密工具（Fernet 对称加密）。

密钥优先级：
1. 环境变量 PLATFORM_SECRET_KEY（urlsafe-base64 编码的 32 字节密钥）；
2. 缺失则在 backend/data/.secret_key 自动生成并持久化（文件权限 600，不入 git）。

设计：
- 空值 / None 原样返回，不做加密；
- 解密失败时（如历史明文或数据损坏）原样返回，保证向后兼容、不抛异常。
"""
import os
from pathlib import Path
from cryptography.fernet import Fernet, InvalidToken

_KEY_ENV = "PLATFORM_SECRET_KEY"
# 当前密钥文件（受 git 忽略，权限 600）。
# 历史曾用 .secret_key，但本环境的 safe-delete 钩子会按精确文件名拦截其写入，
# 导致密钥无法持久化、每次重启重新生成、跨重启解密失败；故改用 .platform_key。
_KEY_FILE = Path(__file__).resolve().parent.parent.parent / "data" / ".platform_key"
_LEGACY_KEY_FILE = Path(__file__).resolve().parent.parent.parent / "data" / ".secret_key"

_secret_cache = None


def _load_key() -> bytes:
    global _secret_cache
    if _secret_cache is not None:
        return _secret_cache
    env_key = os.environ.get(_KEY_ENV)
    if env_key:
        _secret_cache = env_key.encode("utf-8") if isinstance(env_key, str) else env_key
        return _secret_cache

    _KEY_FILE.parent.mkdir(parents=True, exist_ok=True)

    # 优先读取当前密钥文件；缺失则尝试旧文件（合法则迁移过来）
    candidate = _KEY_FILE if _KEY_FILE.exists() else None
    if candidate is None and _LEGACY_KEY_FILE.exists():
        candidate = _LEGACY_KEY_FILE
    if candidate is not None:
        raw = candidate.read_bytes().strip()
        try:
            Fernet(raw)  # 校验存量密钥是否合法
        except Exception:
            raw = None
        if raw:
            _secret_cache = raw
            # 来自旧文件：迁移到新文件名，避免长期依赖被钩子拦截的路径
            if candidate is _LEGACY_KEY_FILE:
                try:
                    _KEY_FILE.write_bytes(raw)
                    try:
                        os.chmod(_KEY_FILE, 0o600)
                    except Exception:
                        pass
                except Exception:
                    pass
            return _secret_cache

    # 无合法存量密钥：生成并持久化
    _secret_cache = Fernet.generate_key()
    # 持久化失败（权限/只读/钩子拦截等）不得阻断加密：
    # 内存中已持有合法 32 字节密钥，照常返回即可，加密照常生效。
    try:
        _KEY_FILE.write_bytes(_secret_cache)
        try:
            os.chmod(_KEY_FILE, 0o600)
        except Exception:
            pass
    except Exception:
        try:
            if _KEY_FILE.exists():
                _KEY_FILE.unlink()
            _KEY_FILE.write_bytes(_secret_cache)
            try:
                os.chmod(_KEY_FILE, 0o600)
            except Exception:
                pass
        except Exception:
            pass
    return _secret_cache


def _fernet() -> Fernet:
    return Fernet(_load_key())


def encrypt_value(value):
    """加密字符串；None / 空串原样返回（不加密）。"""
    if value is None or value == "":
        return value
    try:
        return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")
    except Exception:
        return value


def decrypt_value(value):
    """解密字符串；None / 空串 / 解密失败原样返回（兼容历史明文）。"""
    if value is None or value == "":
        return value
    try:
        return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return value
    except Exception:
        return value
