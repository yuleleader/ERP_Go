# -*- coding: utf-8 -*-
"""
系统备份接口（代理到桌面启动器的本地备份服务）
================================================
后台「系统备份」页面通过本模块与本地启动器（127.0.0.1:25998）联动：
  - GET  /api/system-backup/state   读取备份配置与最近备份日志
  - POST /api/system-backup/run     触发立即备份
  - POST /api/system-backup/config  保存自动备份设置（模式/时间/星期/日期/间隔）

启动器未运行时返回 {ok:false, message:"启动器未运行或本地备份接口不可用..."}，
由前端提示用户先启动桌面启动器。
"""
import json
import urllib.request
import urllib.error

from fastapi import APIRouter, Depends, Body

from ..core.security import require_role

router = APIRouter(prefix="/api/system-backup", tags=["系统备份"])

LAUNCHER_BACKUP_API = "http://127.0.0.1:25998"


def _proxy(method: str, path: str, body=None):
    url = f"{LAUNCHER_BACKUP_API}{path}"
    data = json.dumps(body).encode('utf-8') if body is not None else None
    req = urllib.request.Request(url, method=method, data=data,
                                 headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            raw = resp.read().decode('utf-8')
            return (json.loads(raw) if raw else {'ok': True}), resp.status
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode('utf-8')), e.code
        except Exception:
            return {'ok': False, 'message': f'启动器接口返回错误({e.code})'}, e.code
    except Exception:
        return {'ok': False, 'message': '启动器未运行或本地备份接口不可用（请先启动桌面启动器）'}, 503


@router.get("/state")
async def get_backup_state(_=Depends(require_role("boss"))):
    """读取启动器备份配置与最近备份日志"""
    return _proxy('GET', '/backup/state')[0]


@router.post("/run")
async def run_backup(_=Depends(require_role("boss"))):
    """触发启动器立即备份"""
    return _proxy('POST', '/backup/run')[0]


@router.post("/config")
async def save_backup_config(payload: dict = Body(...), _=Depends(require_role("boss"))):
    """保存自动备份设置（透传 auto_backup 配置）"""
    return _proxy('POST', '/backup/config', payload)[0]
