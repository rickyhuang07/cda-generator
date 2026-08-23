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
- `DATABASE_URL`: PostgreSQL connection string from Supabase
- `DATABASE_PATH`: local SQLite fallback when `DATABASE_URL` is omitted
- `COOKIE_SECURE=true`: required when serving over HTTPS

For SQLite deployments, mount a persistent volume at the directory used by `DATABASE_PATH`. For Supabase deployments, PostgreSQL provides persistent storage and no local database volume is needed. The `/health` endpoint can be used for a hosting health check. A local `.env` file is supported for development and should never be committed.

### Supabase setup

1. Create a Supabase project and set a database password.
2. In Supabase, open **Project Settings > Database > Connect** and copy the connection string. Use the session pooler connection if your hosting provider does not support IPv6.
3. Copy `.env.example` to `.env` and set `DATABASE_URL` to that connection string. The app accepts either `postgresql://...` or `postgresql+psycopg://...`.
4. Set `OWNER_PASSWORD`, `SESSION_SECRET`, and `COOKIE_SECURE=true`.
5. Install dependencies and start the app with `uvicorn app.main:app --host 0.0.0.0 --port 8000`.

The app creates the `submissions` table automatically on startup. To transfer existing local SQLite submissions, set `DATABASE_URL` to Supabase, leave the local `submissions.db` in place, and run `python -m scripts.migrate_sqlite_to_postgres` once. Set `SQLITE_SOURCE` if the source database has another path.

### Vercel deployment

1. Push this project to GitHub, making sure `.env` and `submissions.db` are not committed.
2. In Vercel, choose **Add New Project**, import the repository, and deploy it. The included `vercel.json` uses `api/index.py` as the FastAPI serverless entrypoint.
3. In the Vercel project, open **Settings > Environment Variables** and add `DATABASE_URL`, `OWNER_PASSWORD`, `SESSION_SECRET`, and `COOKIE_SECURE=true` for Production.
4. Set `DATABASE_URL` to the Supabase PostgreSQL connection string. Do not add `SUPABASE_SECRET_KEY` to frontend code or expose it in browser variables.
5. Redeploy after adding the variables. Test `/health`, `/`, and `/owner` on the Vercel domain.

Vercel's filesystem is not persistent, so production must use Supabase through `DATABASE_URL`; do not deploy with the SQLite fallback. Uploaded workbooks are stored in the `submissions` table in Supabase.

An example worksheet and the original Word CDA are in `examples/`.

## Customize

Edit `config/defaults.json` to set:

- Broker name (signature line)
- Brokerage mailing address, email, and phone
- Selling-agent payee addresses keyed by agent name
