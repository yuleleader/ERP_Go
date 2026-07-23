# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from ..core.database import get_db
from ..models.models import LogisticsCompany
from ..schemas.logistics import LogisticsCompanyCreate, LogisticsCompanyUpdate, LogisticsCompanyResponse
from ..core.security import get_current_active_user
from ..models.models import User

router = APIRouter(prefix="/api/logistics", tags=["logistics"])


@router.post("/companies", response_model=LogisticsCompanyResponse)
async def create_logistics_company(
    company: LogisticsCompanyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # 检查公司代码是否已存在
    result = await db.execute(
        select(LogisticsCompany).where(
            (LogisticsCompany.company_code == company.company_code) |
            (LogisticsCompany.company_name == company.company_name)
        )
    )
    existing_company = result.scalars().first()
    if existing_company:
        raise HTTPException(status_code=400, detail="物流公司代码或名称已存在")

    new_company = LogisticsCompany(
        company_code=company.company_code,
        company_name=company.company_name,
        contact_person=company.contact_person,
        contact_phone=company.contact_phone,
        status=company.status,
        created_by=current_user.username
    )
    db.add(new_company)
    await db.commit()
    await db.refresh(new_company)
    return new_company


@router.get("/companies", response_model=List[LogisticsCompanyResponse])
async def get_logistics_companies(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(
        select(LogisticsCompany).offset(skip).limit(limit)
    )
    companies = result.scalars().all()
    return companies


@router.get("/companies/{company_id}", response_model=LogisticsCompanyResponse)
async def get_logistics_company(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(
        select(LogisticsCompany).where(LogisticsCompany.id == company_id)
    )
    company = result.scalars().first()
    if not company:
        raise HTTPException(status_code=404, detail="物流公司不存在")
    return company


@router.put("/companies/{company_id}", response_model=LogisticsCompanyResponse)
async def update_logistics_company(
    company_id: int,
    company: LogisticsCompanyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(
        select(LogisticsCompany).where(LogisticsCompany.id == company_id)
    )
    existing_company = result.scalars().first()
    if not existing_company:
        raise HTTPException(status_code=404, detail="物流公司不存在")

    # 检查公司代码或名称是否与其他公司重复
    result = await db.execute(
        select(LogisticsCompany).where(
            ((LogisticsCompany.company_code == company.company_code) |
             (LogisticsCompany.company_name == company.company_name)) &
            (LogisticsCompany.id != company_id)
        )
    )
    duplicate_company = result.scalars().first()
    if duplicate_company:
        raise HTTPException(status_code=400, detail="物流公司代码或名称已存在")

    for field, value in company.model_dump(exclude_unset=True).items():
        setattr(existing_company, field, value)

    await db.commit()
    await db.refresh(existing_company)
    return existing_company


@router.delete("/companies/{company_id}")
async def delete_logistics_company(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if current_user.role != "boss":
        raise HTTPException(status_code=403, detail="只有管理员可以删除物流公司")

    result = await db.execute(
        select(LogisticsCompany).where(LogisticsCompany.id == company_id)
    )
    company = result.scalars().first()
    if not company:
        raise HTTPException(status_code=404, detail="物流公司不存在")

    await db.delete(company)
    await db.commit()
    return {"message": "物流公司删除成功"}
