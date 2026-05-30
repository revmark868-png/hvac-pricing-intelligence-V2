import os

from sqlalchemy import func, inspect, select, text
from sqlalchemy.orm import Session

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine, get_db
from .importer import import_rows, parse_price_file
from .models import PriceItem, ProjectBid, VendorQuote
from .schemas import (
    BenchmarkOut,
    PriceImportResult,
    PriceItemIn,
    PriceItemOut,
    ProjectBidIn,
    ProjectBidOut,
    VendorQuoteIn,
    VendorQuoteOut,
)

Base.metadata.create_all(bind=engine)


def ensure_schema() -> None:
    inspector = inspect(engine)
    if "vendor_quotes" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("vendor_quotes")}
    if "price_tier" not in columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE vendor_quotes ADD COLUMN price_tier VARCHAR(60) DEFAULT 'distributor'"))


ensure_schema()

app = FastAPI(title="HVAC Pricing Intelligence AI API")

frontend_origins = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/items", response_model=PriceItemOut)
def create_item(payload: PriceItemIn, db: Session = Depends(get_db)):
    item = PriceItem(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@app.get("/items", response_model=list[PriceItemOut])
def list_items(q: str | None = None, category: str | None = None, db: Session = Depends(get_db)):
    stmt = select(PriceItem).order_by(PriceItem.name)
    if q:
        stmt = stmt.where(PriceItem.name.ilike(f"%{q}%"))
    if category:
        stmt = stmt.where(PriceItem.category == category)
    return db.scalars(stmt).all()


@app.post("/quotes", response_model=VendorQuoteOut)
def create_quote(payload: VendorQuoteIn, db: Session = Depends(get_db)):
    item = db.get(PriceItem, payload.item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    quote = VendorQuote(**payload.model_dump())
    db.add(quote)
    db.commit()
    db.refresh(quote)
    return quote


@app.get("/quotes", response_model=list[VendorQuoteOut])
def list_quotes(item_id: int | None = None, vendor: str | None = None, db: Session = Depends(get_db)):
    stmt = select(VendorQuote).order_by(VendorQuote.quote_date.desc(), VendorQuote.id.desc())
    if item_id:
        stmt = stmt.where(VendorQuote.item_id == item_id)
    if vendor:
        stmt = stmt.where(VendorQuote.vendor.ilike(f"%{vendor}%"))
    return db.scalars(stmt).all()


@app.get("/benchmarks", response_model=list[BenchmarkOut])
def benchmarks(q: str | None = None, region: str | None = None, db: Session = Depends(get_db)):
    stmt = (
        select(
            PriceItem.id,
            PriceItem.sku,
            PriceItem.name,
            PriceItem.category,
            PriceItem.brand,
            func.count(VendorQuote.id).label("quote_count"),
            func.min(VendorQuote.unit_cost).label("min_cost"),
            func.avg(VendorQuote.unit_cost).label("avg_cost"),
            func.max(VendorQuote.unit_cost).label("max_cost"),
        )
        .join(VendorQuote, VendorQuote.item_id == PriceItem.id, isouter=True)
        .group_by(PriceItem.id, PriceItem.sku, PriceItem.name, PriceItem.category, PriceItem.brand)
        .order_by(PriceItem.category, PriceItem.name)
    )
    if q:
        stmt = stmt.where(PriceItem.name.ilike(f"%{q}%") | PriceItem.sku.ilike(f"%{q}%"))
    if region:
        stmt = stmt.where((VendorQuote.region == region) | (VendorQuote.region.is_(None)))

    rows = db.execute(stmt).all()
    results = []
    for row in rows:
        best_vendor = None
        if row.min_cost is not None:
            best_vendor = db.scalar(
                select(VendorQuote.vendor)
                .where(VendorQuote.item_id == row.id, VendorQuote.unit_cost == row.min_cost)
                .order_by(VendorQuote.quote_date.desc())
            )
        results.append(
            BenchmarkOut(
                item_id=row.id,
                sku=row.sku,
                name=row.name,
                category=row.category,
                brand=row.brand,
                quote_count=row.quote_count,
                min_cost=row.min_cost,
                avg_cost=row.avg_cost,
                max_cost=row.max_cost,
                best_vendor=best_vendor,
            )
        )
    return results


@app.post("/imports/prices", response_model=PriceImportResult)
async def import_prices(
    file: UploadFile = File(...),
    vendor: str = Form("Imported"),
    region: str = Form("default"),
    price_tier: str = Form("auto"),
    ai_provider: str = Form("rules"),
    commit: bool = Form(False),
    db: Session = Depends(get_db),
):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        rows, ai_used, provider_used = parse_price_file(file.filename or "upload", content, vendor, region, ai_provider, price_tier)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    valid_rows = [row for row in rows if not row.errors and row.unit_cost is not None]
    counts = {"created_items": 0, "created_quotes": 0, "skipped_rows": len(rows) - len(valid_rows)}
    if commit:
        counts = import_rows(db, rows)

    return PriceImportResult(
        filename=file.filename or "upload",
        imported=commit,
        ai_used=ai_used,
        ai_provider=provider_used,
        total_rows=len(rows),
        valid_rows=len(valid_rows),
        invalid_rows=len(rows) - len(valid_rows),
        rows=rows[:500],
        **counts,
    )


def bid_out(bid: ProjectBid) -> ProjectBidOut:
    total_cost = bid.material_cost + bid.labor_cost + bid.subcontractor_cost
    loaded_cost = total_cost * (1 + bid.overhead_rate)
    recommended = loaded_cost / max(1 - bid.target_margin, 0.01)
    sell_price = bid.sell_price or recommended
    actual_margin = (sell_price - loaded_cost) / sell_price if sell_price else 0
    return ProjectBidOut(
        id=bid.id,
        customer=bid.customer,
        project_name=bid.project_name,
        region=bid.region,
        material_cost=bid.material_cost,
        labor_cost=bid.labor_cost,
        subcontractor_cost=bid.subcontractor_cost,
        overhead_rate=bid.overhead_rate,
        target_margin=bid.target_margin,
        sell_price=bid.sell_price,
        status=bid.status,
        total_cost=total_cost,
        recommended_sell_price=recommended,
        actual_margin=actual_margin,
    )


@app.post("/bids", response_model=ProjectBidOut)
def create_bid(payload: ProjectBidIn, db: Session = Depends(get_db)):
    bid = ProjectBid(**payload.model_dump())
    db.add(bid)
    db.commit()
    db.refresh(bid)
    return bid_out(bid)


@app.get("/bids", response_model=list[ProjectBidOut])
def list_bids(db: Session = Depends(get_db)):
    bids = db.scalars(select(ProjectBid).order_by(ProjectBid.created_at.desc())).all()
    return [bid_out(bid) for bid in bids]
