from datetime import date

from pydantic import BaseModel, Field


class PriceItemIn(BaseModel):
    sku: str | None = None
    name: str
    category: str = "equipment"
    brand: str | None = None
    unit: str = "each"
    notes: str | None = None


class PriceItemOut(PriceItemIn):
    id: int

    class Config:
        from_attributes = True


class VendorQuoteIn(BaseModel):
    item_id: int
    vendor: str
    region: str = "default"
    unit_cost: float
    lead_time_days: int | None = None
    quote_date: date = Field(default_factory=date.today)
    source: str | None = None
    notes: str | None = None


class VendorQuoteOut(VendorQuoteIn):
    id: int

    class Config:
        from_attributes = True


class ProjectBidIn(BaseModel):
    customer: str
    project_name: str
    region: str = "default"
    material_cost: float = 0
    labor_cost: float = 0
    subcontractor_cost: float = 0
    overhead_rate: float = 0.12
    target_margin: float = 0.25
    sell_price: float = 0
    status: str = "draft"


class ProjectBidOut(ProjectBidIn):
    id: int
    total_cost: float
    recommended_sell_price: float
    actual_margin: float

    class Config:
        from_attributes = True


class BenchmarkOut(BaseModel):
    item_id: int
    sku: str | None
    name: str
    category: str
    brand: str | None
    quote_count: int
    min_cost: float | None
    avg_cost: float | None
    max_cost: float | None
    best_vendor: str | None = None


class PriceImportRow(BaseModel):
    row_number: int
    sku: str | None = None
    name: str
    category: str = "equipment"
    brand: str | None = None
    unit: str = "each"
    vendor: str
    region: str = "default"
    unit_cost: float | None = None
    lead_time_days: int | None = None
    quote_date: date = Field(default_factory=date.today)
    source: str | None = None
    notes: str | None = None
    confidence: float = 0
    errors: list[str] = Field(default_factory=list)


class PriceImportResult(BaseModel):
    filename: str
    imported: bool
    ai_used: bool
    ai_provider: str = "rules"
    total_rows: int
    valid_rows: int
    invalid_rows: int
    created_items: int = 0
    created_quotes: int = 0
    skipped_rows: int = 0
    rows: list[PriceImportRow]
