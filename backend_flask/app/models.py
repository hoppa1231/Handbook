from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import INTERVAL
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import db


class RequestType(db.Model):
    __tablename__ = "request_types"

    code: Mapped[str] = mapped_column(String(50), primary_key=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)

    requests: Mapped[list["Request"]] = relationship(back_populates="type")


class RequestStatus(db.Model):
    __tablename__ = "request_statuses"

    code: Mapped[str] = mapped_column(String(50), primary_key=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)

    requests: Mapped[list["Request"]] = relationship(back_populates="status_rel")


class ProductCategory(db.Model):
    __tablename__ = "product_categories"

    code: Mapped[str] = mapped_column(String(50), primary_key=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)

    products: Mapped[list["Product"]] = relationship(back_populates="category_rel")


class Supplier(db.Model):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String(200))
    contact: Mapped[Optional[str]] = mapped_column(String(100))
    website: Mapped[Optional[str]] = mapped_column(String(100))
    rating: Mapped[Optional[float]] = mapped_column(Float)

    prices: Mapped[list["SupplierProductPrice"]] = relationship(
        back_populates="supplier", cascade="all, delete-orphan"
    )


class Product(db.Model):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    part_number: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    brand: Mapped[Optional[str]] = mapped_column(String(100))
    model: Mapped[Optional[str]] = mapped_column(String(100))
    serial_number: Mapped[Optional[int]] = mapped_column(Integer)
    scheme: Mapped[Optional[str]] = mapped_column(String(50))
    pos_scheme: Mapped[Optional[str]] = mapped_column(String(100))
    material: Mapped[Optional[str]] = mapped_column(String(100))
    size: Mapped[Optional[str]] = mapped_column(String(300))
    comment: Mapped[Optional[str]] = mapped_column(String(300))
    category: Mapped[Optional[str]] = mapped_column(String(50), ForeignKey("product_categories.code"))

    category_rel: Mapped[Optional[ProductCategory]] = relationship(back_populates="products")
    prices: Mapped[list["SupplierProductPrice"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    request_items: Mapped[list["RequestItem"]] = relationship(back_populates="product")


class Request(db.Model):
    __tablename__ = "requests"
    __table_args__ = (
        UniqueConstraint("id_request", name="uq_requests_id_request"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_request: Mapped[int] = mapped_column(Integer, nullable=False)
    type_request: Mapped[Optional[str]] = mapped_column(String(50), ForeignKey("request_types.code"))
    datetime_coming: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    datetime_delivery: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    status: Mapped[Optional[str]] = mapped_column(String(50), ForeignKey("request_statuses.code"))
    total_price: Mapped[Optional[float]] = mapped_column(Float)

    type: Mapped[Optional[RequestType]] = relationship(back_populates="requests")
    status_rel: Mapped[Optional[RequestStatus]] = relationship(back_populates="requests")
    items: Mapped[list["RequestItem"]] = relationship(
        back_populates="request", cascade="all, delete-orphan"
    )


class SupplierProductPrice(db.Model):
    __tablename__ = "supplier_product_prices"
    __table_args__ = (
        UniqueConstraint("product_id", "supplier_id", name="uq_supplier_product"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), nullable=False)
    supplier_id: Mapped[int] = mapped_column(Integer, ForeignKey("suppliers.id"), nullable=False)
    total_price: Mapped[Optional[float]] = mapped_column(Float)
    lead_time: Mapped[Optional[timedelta]] = mapped_column(INTERVAL)
    cy: Mapped[Optional[float]] = mapped_column(Float)

    product: Mapped[Product] = relationship(back_populates="prices")
    supplier: Mapped[Supplier] = relationship(back_populates="prices")


class RequestItem(db.Model):
    __tablename__ = "request_items"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="chk_request_items_quantity"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    part_number: Mapped[Optional[str]] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity: Mapped[Optional[int]] = mapped_column(Integer)
    unit: Mapped[Optional[str]] = mapped_column(String(20))
    brand: Mapped[Optional[str]] = mapped_column(String(100))
    model: Mapped[Optional[str]] = mapped_column(String(100))
    serial_number: Mapped[Optional[int]] = mapped_column(Integer)
    scheme: Mapped[Optional[str]] = mapped_column(String(50))
    pos_scheme: Mapped[Optional[str]] = mapped_column(String(100))
    material: Mapped[Optional[str]] = mapped_column(String(100))
    comment: Mapped[Optional[str]] = mapped_column(String(300))
    unit_price: Mapped[Optional[float]] = mapped_column(Float)
    total_price: Mapped[Optional[float]] = mapped_column(Float)
    request_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("requests.id"))
    product_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("products.id"))

    request: Mapped[Optional[Request]] = relationship(back_populates="items")
    product: Mapped[Optional[Product]] = relationship(back_populates="request_items")
