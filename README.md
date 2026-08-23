# CDA Generator

Turns a RealtyOne Plus **DATA WORKSHEET** Excel file into a Commission Disbursement Authorization PDF.

The worksheet layout is the ROP sale/lease sheet (property, parties, title, and commission rows). Brokerage letterhead, broker name, and agent payee mailing addresses live in `config/defaults.json` because those values are not on the worksheet.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). A submitter can upload a `.xlsx` worksheet or complete the required fields manually. Submissions are stored in SQLite for owner review at [http://127.0.0.1:8000/owner](http://127.0.0.1:8000/owner), where the owner can inspect an entry and generate its PDF.

For local development, leaving `OWNER_PASSWORD` unset keeps the owner page open. Before deploying to a shared or public network, configure `OWNER_PASSWORD`, `SESSION_SECRET`, and `COOKIE_SECURE=true`.

## Deploy

The backend runs with Uvicorn and can be deployed with the included `Dockerfile`. Configure these environment variables in your hosting provider:

- `OWNER_PASSWORD`: required password for the owner workspace
- `SESSION_SECRET`: long random value used to sign the owner session
- `DATABASE_PATH`: persistent path for SQLite, such as `/data/submissions.db`
- `COOKIE_SECURE=true`: required when serving over HTTPS

Mount a persistent volume at the directory used by `DATABASE_PATH`; otherwise submissions will be lost when the container restarts. The `/health` endpoint can be used for a hosting health check. A local `.env` file is supported for development and should never be committed.

An example worksheet and the original Word CDA are in `examples/`.

## Customize

Edit `config/defaults.json` to set:

- Broker name (signature line)
- Brokerage mailing address, email, and phone
- Selling-agent payee addresses keyed by agent name
