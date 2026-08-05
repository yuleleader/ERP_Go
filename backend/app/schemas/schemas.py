# -*- coding: utf-8 -*-
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UserBase(BaseModel):
    username: str
    real_name: Optional[str] = None
    role: str = "sales"
    commission_rate: Optional[int] = Field(None, ge=1, le=100)
    is_active: bool = True

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserUpdate(BaseModel):
    real_name: Optional[str] = None
    role: Optional[str] = None
    commission_rate: Optional[int] = Field(None, ge=1, le=100)
    is_active: Optional[bool] = None

class UserResponse(UserBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    username: str
    password: str

class ShopBase(BaseModel):
    shop_name: str
    shop_account: str
    status: str = "normal"

class ShopCreate(ShopBase):
    pass

class ShopUpdate(BaseModel):
    shop_name: Optional[str] = None
    shop_account: Optional[str] = None
    status: Optional[str] = None

class ShopResponse(ShopBase):
    id: int
    shop_id: str
    creator: Optional[str] = None
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None
    order_count: Optional[int] = 0

    class Config:
        from_attributes = True

class OrderBase(BaseModel):
    product_name: Optional[str] = None
    platform_order_no: Optional[str] = None
    sales_amount: Optional[str] = None
    freight: Optional[str] = None
    shipping_status: str = "pending"
    logistics_company: Optional[str] = None
    logistics_no: Optional[str] = None
    receiver_address: Optional[str] = None
    remark: Optional[str] = None

class OrderCreate(OrderBase):
    shop_id: str
    created_at: Optional[datetime] = None

class OrderUpdate(BaseModel):
    shop_id: Optional[str] = None
    platform_order_no: Optional[str] = None
    product_name: Optional[str] = None
    sales_amount: Optional[str] = None
    shipping_status: Optional[str] = None
    logistics_company: Optional[str] = None
    logistics_no: Optional[str] = None
    freight: Optional[str] = None
    receiver_address: Optional[str] = None
    remark: Optional[str] = None
    created_at: Optional[datetime] = None
    shipping_time: Optional[datetime] = None
    produce_status: Optional[str] = None

class OrderResponse(OrderBase):
    id: int
    order_id: str
    shop_id: Optional[str] = None
    shipping_operator: Optional[str] = None
    shipping_time: Optional[datetime] = None
    commission_rate: Optional[int] = None
    commission_amount: Optional[str] = None
    created_by: Optional[str] = None
    creator_real_name: Optional[str] = None
    created_at: Optional[datetime] = None
    order_days: Optional[int] = None
    produce_status: Optional[str] = None
    produce_status_update_at: Optional[datetime] = None
    produce_status_update_user: Optional[str] = None

    class Config:
        from_attributes = True

class ImageBase(BaseModel):
    image_type: Optional[str] = None
    image_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    is_main: int = 0

class ImageCreate(ImageBase):
    order_id: Optional[str] = None
    temp_id: Optional[str] = None

class ImageResponse(ImageBase):
    id: int
    order_id: Optional[str] = None
    uploaded_by: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class OperationLogResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    username: Optional[str] = None
    operation_type: str
    operation_content: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class LoginLogResponse(BaseModel):
    id: int
    username: str
    login_time: Optional[datetime] = None
    ip_address: Optional[str] = None
    status: str

    class Config:
        from_attributes = True

class SystemSettingResponse(BaseModel):
    id: int
    key: str
    value: Optional[str] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True

class SystemSettingUpdate(BaseModel):
    value: str
    description: Optional[str] = None

# ==================== 商品管理相关 Schema ====================

class ProductBase(BaseModel):
    """商品基础模型"""
    product_name: str = Field(..., min_length=2, max_length=100, description="商品名称，2-100字符")
    product_remark: Optional[str] = Field(None, max_length=500, description="商品备注，最大500字符")

class ProductCreate(ProductBase):
    """商品创建模型"""
    pass

class ProductUpdate(BaseModel):
    """商品更新模型"""
    product_name: Optional[str] = Field(None, min_length=2, max_length=100, description="商品名称，2-100字符")
    product_remark: Optional[str] = Field(None, max_length=500, description="商品备注，最大500字符")
    status: Optional[str] = Field(None, description="商品状态：active/inactive")

class ProductResponse(ProductBase):
    """商品响应模型"""
    id: int
    product_code: str
    status: str = "active"
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
