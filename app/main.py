from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from app.parser import parse_rop_xlsx
from app.pdf import build_cda_pdf

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"

app = FastAPI(title="CDA Generator", version="1.0.0")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.post("/api/preview")
async def preview(
    file: UploadFile = File(...),
    overrides: str = Form("{}"),
):
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=400, detail="Upload a RealtyOne Plus .xlsx data worksheet.")
    payload = json.loads(overrides or "{}")
    with NamedTemporaryFile(suffix=".xlsx", delete=True) as tmp:
        tmp.write(await file.read())
        tmp.flush()
        tx = parse_rop_xlsx(Path(tmp.name), payload)
    return tx.to_preview()


@app.post("/api/generate")
async def generate(
    file: UploadFile = File(...),
    overrides: str = Form("{}"),
):
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=400, detail="Upload a RealtyOne Plus .xlsx data worksheet.")
    payload = json.loads(overrides or "{}")
    with NamedTemporaryFile(suffix=".xlsx", delete=True) as tmp:
        tmp.write(await file.read())
        tmp.flush()
        tx = parse_rop_xlsx(Path(tmp.name), payload)
    pdf = build_cda_pdf(tx)
    filename = tx.suggested_filename()
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
