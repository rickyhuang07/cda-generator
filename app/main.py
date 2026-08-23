from __future__ import annotations

import json
import hashlib
import hmac
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import Column, LargeBinary, MetaData, String, Table, Text, create_engine, delete, select, update
from dotenv import load_dotenv

from app.parser import parse_rop_xlsx, transaction_from_overrides
from app.pdf import build_cda_pdf

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"
load_dotenv(ROOT / ".env")
DB_PATH = Path(os.getenv("DATABASE_PATH", ROOT / "submissions.db"))
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")
if DATABASE_URL.startswith(("postgres://", "postgresql://")):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1).replace("postgresql://", "postgresql+psycopg://", 1)
OWNER_PASSWORD = os.getenv("OWNER_PASSWORD", "")
SESSION_SECRET = os.getenv("SESSION_SECRET", "local-development-secret")
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
metadata = MetaData()
submissions_table = Table(
    "submissions",
    metadata,
    Column("id", String(32), primary_key=True),
    Column("created_at", String(40), nullable=False),
    Column("status", String(20), nullable=False),
    Column("filename", String(255)),
    Column("workbook", LargeBinary),
    Column("overrides", Text, nullable=False),
)

app = FastAPI(title="CDA Generator", version="1.0.0")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.exception_handler(Exception)
async def internal_error(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": str(exc) or "Internal server error"})


def db():
    if DATABASE_URL.startswith("sqlite"):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    metadata.create_all(engine)
    return engine


def require_owner(request: Request) -> None:
    if not OWNER_PASSWORD or not SESSION_SECRET or SESSION_SECRET == "local-development-secret":
        raise HTTPException(status_code=503, detail="Owner authentication is not configured")
    expected = hmac.new(SESSION_SECRET.encode(), b"owner", hashlib.sha256).hexdigest()
    if not hmac.compare_digest(request.cookies.get("owner_session", ""), expected):
        raise HTTPException(status_code=401, detail="Owner login required")


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


def preview_data(tx) -> dict:
    data = tx.to_preview()
    data["title_company_address"] = getattr(tx, "title_company_address", "")
    return data


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/owner")
def owner() -> FileResponse:
    response = FileResponse(STATIC / "owner.html")
    response.delete_cookie("owner_session")
    return response


@app.get("/health")
def health():
    with db().connect() as connection:
        connection.execute(select(1))
    return {"status": "ok"}


@app.post("/api/owner/login")
def owner_login(password: str = Form(...)):
    if not OWNER_PASSWORD or not SESSION_SECRET or SESSION_SECRET == "local-development-secret":
        raise HTTPException(status_code=503, detail="Owner authentication is not configured")
    if not hmac.compare_digest(password, OWNER_PASSWORD):
        raise HTTPException(status_code=401, detail="Invalid owner password")
    expected = hmac.new(SESSION_SECRET.encode(), b"owner", hashlib.sha256).hexdigest()
    response = JSONResponse({"message": "Signed in"})
    response.set_cookie("owner_session", expected, httponly=True, secure=COOKIE_SECURE, samesite="lax")
    return response


@app.post("/api/owner/logout")
def owner_logout():
    response = JSONResponse({"message": "Signed out"})
    response.delete_cookie("owner_session")
    return response


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
    return preview_data(tx)


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
    with db().begin() as connection:
        connection.execute(
            submissions_table.insert().values(
                id=submission_id,
                created_at=datetime.now(timezone.utc).isoformat(),
                status="pending",
                filename=filename,
                workbook=workbook,
                overrides=json.dumps(payload),
            )
        )
    return {"id": submission_id, "message": "Submission sent for owner review."}


@app.get("/api/submissions")
def submissions(request: Request):
    require_owner(request)
    with db().connect() as connection:
        rows = connection.execute(
            select(submissions_table.c.id, submissions_table.c.created_at, submissions_table.c.status, submissions_table.c.filename, submissions_table.c.overrides)
            .order_by(submissions_table.c.created_at.desc())
        ).mappings().all()
    return [dict(row, overrides=json.loads(row["overrides"])) for row in rows]


@app.get("/api/submissions/{submission_id}")
def submission(submission_id: str, request: Request):
    require_owner(request)
    with db().connect() as connection:
        row = connection.execute(select(submissions_table).where(submissions_table.c.id == submission_id)).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Submission not found")
    return {"id": row["id"], "created_at": row["created_at"], "status": row["status"], "filename": row["filename"], "preview": preview_data(submission_transaction(row))}


@app.delete("/api/submissions/{submission_id}")
def delete_submission(submission_id: str, request: Request):
    require_owner(request)
    with db().begin() as connection:
        result = connection.execute(delete(submissions_table).where(submissions_table.c.id == submission_id))
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Submission not found")
    return {"id": submission_id, "message": "Submission deleted."}


def submission_transaction(row):
    payload = json.loads(row["overrides"])
    if row["workbook"]:
        with NamedTemporaryFile(suffix=".xlsx", delete=True) as tmp:
            tmp.write(row["workbook"])
            tmp.flush()
            return parse_rop_xlsx(Path(tmp.name), payload)
    return transaction_from_overrides(payload)


@app.post("/api/submissions/{submission_id}/generate")
def generate_submission(submission_id: str, request: Request):
    require_owner(request)
    with db().connect() as connection:
        row = connection.execute(select(submissions_table).where(submissions_table.c.id == submission_id)).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Submission not found")
    tx = submission_transaction(row)
    pdf = build_cda_pdf(tx)
    with db().begin() as connection:
        connection.execute(update(submissions_table).where(submissions_table.c.id == submission_id).values(status="generated"))
    return Response(content=pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{tx.suggested_filename()}"'})
