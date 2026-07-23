# -*- coding: utf-8 -*-
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class LogisticsCompanyBase(BaseModel):
    company_code: str = Field(..., description="物流公司代码")
    company_name: str = Field(..., description="物流公司名称")
    contact_person: Optional[str] = Field(None, description="联系人")
    contact_phone: Optional[str] = Field(None, description="联系电话")
    status: str = Field(default="active", description="状态")


class LogisticsCompanyCreate(LogisticsCompanyBase):
    pass


class LogisticsCompanyUpdate(BaseModel):
    company_code: Optional[str] = Field(None, description="物流公司代码")
    company_name: Optional[str] = Field(None, description="物流公司名称")
    contact_person: Optional[str] = Field(None, description="联系人")
    contact_phone: Optional[str] = Field(None, description="联系电话")
    status: Optional[str] = Field(None, description="状态")


class LogisticsCompanyResponse(LogisticsCompanyBase):
    id: int
    created_by: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
