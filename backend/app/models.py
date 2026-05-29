from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class PriceItem(Base):
    __tablename__ = "price_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sku: Mapped[str | None] = mapped_column(String(100), index=True)
    name: Mapped[str] = mapped_column(String(260), index=True)
    category: Mapped[str] = mapped_column(String(80), default="equipment", index=True)
    brand: Mapped[str | None] = mapped_column(String(140), index=True)
    unit: Mapped[str] = mapped_column(String(40), default="each")
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    quotes: Mapped[list["VendorQuote"]] = relationship(back_populates="item", cascade="all, delete-orphan")


class VendorQuote(Base):
    __tablename__ = "vendor_quotes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("price_items.id", ondelete="CASCADE"), index=True)
    vendor: Mapped[str] = mapped_column(String(180), index=True)
    region: Mapped[str] = mapped_column(String(100), default="default", index=True)
    unit_cost: Mapped[float] = mapped_column(Float)
    lead_time_days: Mapped[int | None] = mapped_column(Integer)
    quote_date: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    source: Mapped[str | None] = mapped_column(String(240))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    item: Mapped[PriceItem] = relationship(back_populates="quotes")


class ProjectBid(Base):
    __tablename__ = "project_bids"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    customer: Mapped[str] = mapped_column(String(180), index=True)
    project_name: Mapped[str] = mapped_column(String(220), index=True)
    region: Mapped[str] = mapped_column(String(100), default="default", index=True)
    material_cost: Mapped[float] = mapped_column(Float, default=0)
    labor_cost: Mapped[float] = mapped_column(Float, default=0)
    subcontractor_cost: Mapped[float] = mapped_column(Float, default=0)
    overhead_rate: Mapped[float] = mapped_column(Float, default=0.12)
    target_margin: Mapped[float] = mapped_column(Float, default=0.25)
    sell_price: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
