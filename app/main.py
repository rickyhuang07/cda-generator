from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from app.parser import parse_rop_xlsx, transaction_from_overrides
from app.pdf import build_cda_pdf

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"
DB_PATH = ROOT / "submissions.db"

app = FastAPI(title="CDA Generator", version="1.0.0")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.exception_handler(Exception)
async def internal_error(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": str(exc) or "Internal server error"})


def db() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """CREATE TABLE IF NOT EXISTS submissions (
            id TEXT PRIMARY KEY, created_at TEXT NOT NULL, status TEXT NOT NULL,
            filename TEXT, workbook BLOB, overrides TEXT NOT NULL
        )"""
    )
    connection.commit()
    return connection


def required_fields(payload: dict) -> list[str]:
    fields = {
        "closer": "Escrow Agent",
        "closer_email": "Escrow Agent's Email",
        "closer_phone": "Escrow Agent's Phone",
        "title_company": "Title Company",
        "title_company_address": "Title Company Address",
        "escrow_no": "Escrow Number",
        "gross_commission": "Gross Commission",
        "mls": "MLS",
        "sale_price": "Sale Price",
        "property_address": "Property address",
        "close_date": "Closing date",
        "seller": "Seller / landlord",
        "buyer": "Buyer / tenant",
        "selling_agent": "Selling agent",
        "broker_process_fees": "Broker Process Fees",
        "selling_agent_commission": "Agent commission",
        "agent_payee_address": "Agent payee mailing address",
    }
    return [label for key, label in fields.items() if not str(payload.get(key, "")).strip()]


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/owner")
def owner() -> FileResponse:
    return FileResponse(STATIC / "owner.html")


@app.post("/api/preview")
async def preview(
    file: UploadFile | None = File(None),
    overrides: str = Form("{}"),
):
    if file is None or not file.filename or not file.filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=400, detail="Upload a RealtyOne Plus .xlsx data worksheet.")
    payload = json.loads(overrides or "{}")
    with NamedTemporaryFile(suffix=".xlsx", delete=True) as tmp:
        tmp.write(await file.read())
        tmp.flush()
        tx = parse_rop_xlsx(Path(tmp.name), payload)
    return tx.to_preview()


@app.post("/api/submissions")
async def submit(
    file: UploadFile | None = File(None),
    overrides: str = Form("{}"),
):
    payload = json.loads(overrides or "{}")
    workbook = None
    filename = None
    if file and file.filename:
        if not file.filename.lower().endswith((".xlsx", ".xlsm")):
            raise HTTPException(status_code=400, detail="Upload an .xlsx or .xlsm worksheet.")
        workbook = await file.read()
        filename = file.filename
        with NamedTemporaryFile(suffix=".xlsx", delete=True) as tmp:
            tmp.write(workbook)
            tmp.flush()
            tx = parse_rop_xlsx(Path(tmp.name), payload)
    missing = required_fields(payload)
    if missing:
        raise HTTPException(status_code=400, detail="Required fields missing: " + ", ".join(missing))
    if not workbook:
        tx = transaction_from_overrides(payload)

    submission_id = uuid.uuid4().hex[:12]
    connection = db()
    connection.execute(
        "INSERT INTO submissions VALUES (?, datetime('now'), 'pending', ?, ?, ?)",
        (submission_id, filename, workbook, json.dumps(payload)),
    )
    connection.commit()
    connection.close()
    return {"id": submission_id, "message": "Submission sent for owner review."}


@app.get("/api/submissions")
def submissions():
    connection = db()
    rows = connection.execute(
        "SELECT id, created_at, status, filename, overrides FROM submissions ORDER BY created_at DESC"
    ).fetchall()
    connection.close()
    return [dict(row, overrides=json.loads(row["overrides"])) for row in rows]


@app.get("/api/submissions/{submission_id}")
def submission(submission_id: str):
    connection = db()
    row = connection.execute("SELECT * FROM submissions WHERE id = ?", (submission_id,)).fetchone()
    connection.close()
    if not row:
        raise HTTPException(status_code=404, detail="Submission not found")
    return {"id": row["id"], "created_at": row["created_at"], "status": row["status"], "filename": row["filename"], "preview": submission_transaction(row).to_preview()}


def submission_transaction(row: sqlite3.Row):
    payload = json.loads(row["overrides"])
    if row["workbook"]:
        with NamedTemporaryFile(suffix=".xlsx", delete=True) as tmp:
            tmp.write(row["workbook"])
            tmp.flush()
            return parse_rop_xlsx(Path(tmp.name), payload)
    return transaction_from_overrides(payload)


@app.post("/api/submissions/{submission_id}/generate")
def generate_submission(submission_id: str):
    connection = db()
    row = connection.execute("SELECT * FROM submissions WHERE id = ?", (submission_id,)).fetchone()
    connection.close()
    if not row:
        raise HTTPException(status_code=404, detail="Submission not found")
    tx = submission_transaction(row)
    pdf = build_cda_pdf(tx)
    connection = db()
    connection.execute("UPDATE submissions SET status = 'generated' WHERE id = ?", (submission_id,))
    connection.commit()
    connection.close()
    return Response(content=pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{tx.suggested_filename()}"'})
