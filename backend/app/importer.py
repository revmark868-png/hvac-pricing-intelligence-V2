import csv
import io
import json
import os
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import PriceItem, VendorQuote
from .schemas import PriceImportRow

FIELD_ALIASES: dict[str, list[str]] = {
    "sku": ["sku", "model", "model number", "part", "part no", "part number", "item", "catalog", "型号", "料号", "编号"],
    "name": ["name", "description", "desc", "product", "item description", "equipment", "material", "产品", "描述", "说明", "名称"],
    "category": ["category", "type", "class", "group", "equipment", "material", "labor", "类别", "类型"],
    "brand": ["brand", "manufacturer", "make", "mfg", "品牌", "厂家", "厂牌"],
    "unit": ["unit", "uom", "unit of measure", "单位"],
    "vendor": ["vendor", "supplier", "dealer", "distributor", "供应商", "经销商"],
    "region": ["region", "market", "branch", "location", "区域", "地区"],
    "unit_cost": ["price", "cost", "unit price", "unit cost", "net", "amount", "报价", "价格", "单价", "成本"],
    "lead_time_days": ["lead", "lead time", "days", "eta", "交期", "天数"],
    "quote_date": ["date", "quote date", "effective", "有效期", "日期"],
}

CATEGORY_HINTS = {
    "labor": ["labor", "install", "service", "hour", "工时", "人工", "安装"],
    "material": ["refrigerant", "copper", "line set", "filter", "pad", "wire", "材料", "冷媒", "铜管"],
    "equipment": ["condenser", "furnace", "coil", "handler", "heat pump", "mini split", "seer", "ton", "设备", "主机"],
}

PRICE_RE = re.compile(r"(?<![A-Za-z0-9])[$¥￥]?\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.([0-9]{1,4}))?(?![A-Za-z0-9])")


@dataclass
class ParsedTable:
    headers: list[str]
    rows: list[list[str]]


def normalize(value: Any) -> str:
    return str(value or "").replace("\u00a0", " ").strip()


def compact(value: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", value.lower()).strip()


def parse_price(value: str) -> float | None:
    candidates: list[float] = []
    for match in PRICE_RE.finditer((value or "").replace(" ", "")):
        whole = match.group(1).replace(",", "")
        decimal = match.group(2) or ""
        try:
            number = float(f"{whole}.{decimal}" if decimal else whole)
            if number >= 0:
                candidates.append(number)
        except ValueError:
            continue
    return max(candidates) if candidates else None


def parse_int(value: str) -> int | None:
    match = re.search(r"\d+", value or "")
    return int(match.group(0)) if match else None


def parse_date(value: str) -> date:
    text = normalize(value)
    if not text:
        return date.today()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%Y/%m/%d", "%m-%d-%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return date.today()


def detect_category(*values: str) -> str:
    text = compact(" ".join(values))
    for category, hints in CATEGORY_HINTS.items():
        if any(hint in text for hint in hints):
            return category
    return "equipment"


def pad_rows(rows: list[list[str]], width: int) -> list[list[str]]:
    return [row[:width] + [""] * max(width - len(row), 0) for row in rows]


def score_header_row(row: list[str]) -> int:
    score = 0
    for cell in [compact(cell) for cell in row]:
        for aliases in FIELD_ALIASES.values():
            if any(alias in cell for alias in aliases):
                score += 2
        if cell:
            score += 1
    return score


def choose_header(rows: list[list[str]]) -> ParsedTable:
    rows = [[normalize(cell) for cell in row] for row in rows if any(normalize(cell) for cell in row)]
    if not rows:
        return ParsedTable(headers=[], rows=[])

    header_index, best_score = max(
        [(index, score_header_row(row)) for index, row in enumerate(rows[:20])],
        key=lambda item: item[1],
    )
    if best_score < 3:
        width = max(len(row) for row in rows)
        return ParsedTable(headers=[f"Column {index + 1}" for index in range(width)], rows=pad_rows(rows, width))

    width = max(len(row) for row in rows[header_index:])
    headers = pad_rows([rows[header_index]], width)[0]
    headers = [header or f"Column {index + 1}" for index, header in enumerate(headers)]
    return ParsedTable(headers=headers, rows=pad_rows(rows[header_index + 1 :], width))


def detect_mapping(headers: list[str], rows: list[list[str]]) -> dict[str, int | None]:
    mapping: dict[str, int | None] = {field: None for field in FIELD_ALIASES}
    normalized_headers = [compact(header) for header in headers]

    for field, aliases in FIELD_ALIASES.items():
        alias_tokens = [compact(alias) for alias in aliases]
        best_score = 0
        best_index: int | None = None
        for index, header in enumerate(normalized_headers):
            score = sum(1 for alias in alias_tokens if alias and alias in header)
            if field == "unit_cost":
                score += sum(1 for row in rows[:20] if index < len(row) and parse_price(row[index]) is not None)
            if score > best_score:
                best_score = score
                best_index = index
        mapping[field] = best_index if best_score > 0 else None

    if mapping["unit_cost"] is None and rows:
        scores = [
            (sum(1 for row in rows[:40] if index < len(row) and parse_price(row[index]) is not None), index)
            for index in range(len(headers))
        ]
        best_count, best_index = max(scores, default=(0, 0))
        if best_count:
            mapping["unit_cost"] = best_index

    return mapping


def value(row: list[str], mapping: dict[str, int | None], field: str) -> str:
    index = mapping.get(field)
    return normalize(row[index]) if index is not None and index < len(row) else ""


def table_to_rows(table: ParsedTable, default_vendor: str, default_region: str, source: str) -> list[PriceImportRow]:
    mapping = detect_mapping(table.headers, table.rows)
    parsed_rows: list[PriceImportRow] = []

    for index, row in enumerate(table.rows, start=2):
        sku = value(row, mapping, "sku")
        name = value(row, mapping, "name") or sku
        brand = value(row, mapping, "brand") or None
        category = value(row, mapping, "category") or detect_category(name, sku, brand or "")
        unit = value(row, mapping, "unit") or "each"
        vendor = value(row, mapping, "vendor") or default_vendor
        region = value(row, mapping, "region") or default_region
        price_text = value(row, mapping, "unit_cost") or " ".join(row)
        unit_cost = parse_price(price_text)
        errors = []
        if not name:
            errors.append("Missing item name or model")
        if unit_cost is None:
            errors.append("Missing valid price")
        if not vendor:
            errors.append("Missing vendor")

        if name or sku or unit_cost is not None:
            parsed_rows.append(
                PriceImportRow(
                    row_number=index,
                    sku=sku or None,
                    name=name,
                    category=category.lower(),
                    brand=brand,
                    unit=unit,
                    vendor=vendor,
                    region=region,
                    unit_cost=unit_cost,
                    lead_time_days=parse_int(value(row, mapping, "lead_time_days")),
                    quote_date=parse_date(value(row, mapping, "quote_date")),
                    source=source,
                    notes=None,
                    confidence=min(1, 0.35 + (0.2 if sku else 0) + (0.2 if name else 0) + (0.25 if unit_cost is not None else 0) + (0.1 if vendor else 0)),
                    errors=errors,
                )
            )
    return parsed_rows


def parse_csv_like(content: bytes, delimiter: str) -> ParsedTable:
    text = content.decode("utf-8-sig", errors="replace")
    return choose_header(list(csv.reader(io.StringIO(text), delimiter=delimiter)))


def parse_excel(content: bytes) -> ParsedTable:
    from openpyxl import load_workbook

    workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    sheet = workbook[workbook.sheetnames[0]]
    rows = [[normalize(cell) for cell in row] for row in sheet.iter_rows(values_only=True)]
    return choose_header(rows)


def parse_pdf(content: bytes) -> ParsedTable:
    import pdfplumber

    rows: list[list[str]] = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables() or []:
                rows.extend([[normalize(cell) for cell in row] for row in table])
            text = page.extract_text() or ""
            for line in text.splitlines():
                cells = [part for part in re.split(r"\s{2,}|\t+", line.strip()) if part]
                if len(cells) >= 2 and any(parse_price(cell) is not None for cell in cells):
                    rows.append(cells)
    return choose_header(rows)


def ai_normalize_rows(rows: list[PriceImportRow], default_vendor: str, default_region: str, source: str) -> tuple[list[PriceImportRow], bool]:
    if not os.getenv("OPENAI_API_KEY") or not rows:
        return rows, False

    try:
        from openai import OpenAI

        client = OpenAI()
        payload = [row.model_dump(mode="json") for row in rows[:200]]
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "rows": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "row_number": {"type": "integer"},
                            "sku": {"type": ["string", "null"]},
                            "name": {"type": "string"},
                            "category": {"type": "string", "enum": ["equipment", "material", "labor", "subcontractor", "other"]},
                            "brand": {"type": ["string", "null"]},
                            "unit": {"type": "string"},
                            "vendor": {"type": "string"},
                            "region": {"type": "string"},
                            "unit_cost": {"type": ["number", "null"]},
                            "lead_time_days": {"type": ["integer", "null"]},
                            "quote_date": {"type": "string"},
                            "notes": {"type": ["string", "null"]},
                            "confidence": {"type": "number"},
                            "errors": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["row_number", "sku", "name", "category", "brand", "unit", "vendor", "region", "unit_cost", "lead_time_days", "quote_date", "notes", "confidence", "errors"],
                    },
                }
            },
            "required": ["rows"],
        }
        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            input=(
                "Normalize HVAC vendor price rows into clean JSON. Keep prices numeric. "
                "Use defaults when missing: vendor=" + default_vendor + ", region=" + default_region + ". "
                "Return only rows that look like price records. Source file: " + source + "\n\n" + json.dumps(payload, ensure_ascii=False)
            ),
            text={"format": {"type": "json_schema", "name": "hvac_price_rows", "schema": schema, "strict": True}},
        )
        data = json.loads(response.output_text)
        normalized = []
        for item in data.get("rows", []):
            item["quote_date"] = parse_date(str(item.get("quote_date") or ""))
            normalized.append(PriceImportRow(**item, source=source))
        return normalized or rows, True
    except Exception:
        return rows, False


def parse_price_file(filename: str, content: bytes, default_vendor: str = "Imported", default_region: str = "default") -> tuple[list[PriceImportRow], bool]:
    extension = Path(filename).suffix.lower()
    if extension == ".csv":
        table = parse_csv_like(content, ",")
    elif extension == ".tsv":
        table = parse_csv_like(content, "\t")
    elif extension in {".xlsx", ".xlsm", ".xltx", ".xltm"}:
        table = parse_excel(content)
    elif extension == ".pdf":
        table = parse_pdf(content)
    else:
        raise ValueError("Unsupported file type. Upload .xlsx, .csv, .tsv, or .pdf.")

    rows = table_to_rows(table, default_vendor, default_region, filename)
    return ai_normalize_rows(rows, default_vendor, default_region, filename)


def import_rows(db: Session, rows: list[PriceImportRow]) -> dict[str, int]:
    created_items = 0
    created_quotes = 0
    skipped_rows = 0

    for row in rows:
        if row.errors or row.unit_cost is None:
            skipped_rows += 1
            continue

        item = db.scalar(select(PriceItem).where(PriceItem.sku == row.sku)) if row.sku else None
        if not item:
            item = db.scalar(select(PriceItem).where(PriceItem.name == row.name, PriceItem.category == row.category))
        if not item:
            item = PriceItem(sku=row.sku, name=row.name, category=row.category, brand=row.brand, unit=row.unit, notes=row.notes)
            db.add(item)
            db.flush()
            created_items += 1

        db.add(
            VendorQuote(
                item_id=item.id,
                vendor=row.vendor,
                region=row.region,
                unit_cost=row.unit_cost,
                lead_time_days=row.lead_time_days,
                quote_date=row.quote_date,
                source=row.source,
                notes=row.notes,
            )
        )
        created_quotes += 1

    db.commit()
    return {"created_items": created_items, "created_quotes": created_quotes, "skipped_rows": skipped_rows}
