from datetime import date

from .database import Base, SessionLocal, engine
from .models import PriceItem, VendorQuote

Base.metadata.create_all(bind=engine)

seed_items = [
    {"sku": "COND-3T-14", "name": "3 Ton 14 SEER Condenser", "category": "equipment", "brand": "Generic", "unit": "each"},
    {"sku": "R410A-25LB", "name": "R410A Refrigerant 25 lb", "category": "material", "brand": None, "unit": "jug"},
    {"sku": "LAB-INSTALL", "name": "Install Labor", "category": "labor", "brand": None, "unit": "hour"},
]

seed_quotes = [
    ("3 Ton 14 SEER Condenser", "Vendor A", "DFW", 1580, 3),
    ("3 Ton 14 SEER Condenser", "Vendor B", "DFW", 1645, 2),
    ("R410A Refrigerant 25 lb", "Vendor A", "DFW", 315, 1),
    ("R410A Refrigerant 25 lb", "Vendor C", "DFW", 342, 1),
    ("Install Labor", "Internal", "DFW", 95, None),
]


def run():
    db = SessionLocal()
    try:
        for item_data in seed_items:
            existing = db.query(PriceItem).filter(PriceItem.sku == item_data["sku"]).first()
            if not existing:
                db.add(PriceItem(**item_data))
        db.commit()

        for item_name, vendor, region, unit_cost, lead_time in seed_quotes:
            item = db.query(PriceItem).filter(PriceItem.name == item_name).first()
            exists = db.query(VendorQuote).filter(
                VendorQuote.item_id == item.id,
                VendorQuote.vendor == vendor,
                VendorQuote.unit_cost == unit_cost,
            ).first()
            if not exists:
                db.add(VendorQuote(item_id=item.id, vendor=vendor, region=region, unit_cost=unit_cost, lead_time_days=lead_time, quote_date=date.today(), source="seed"))
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    run()
