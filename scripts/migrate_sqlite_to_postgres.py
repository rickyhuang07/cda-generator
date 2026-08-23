from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, select

from app.main import db, submissions_table


source_path = Path(os.getenv("SQLITE_SOURCE", "submissions.db"))
if not source_path.exists():
    raise SystemExit(f"SQLite source not found: {source_path}")

source = create_engine(f"sqlite:///{source_path}")
target = db()

with source.connect() as source_connection, target.begin() as target_connection:
    rows = source_connection.execute(select(submissions_table)).mappings().all()
    for row in rows:
        existing = target_connection.execute(
            select(submissions_table.c.id).where(submissions_table.c.id == row["id"])
        ).first()
        if existing is None:
            target_connection.execute(submissions_table.insert().values(**dict(row)))

print(f"Migrated {len(rows)} submission(s) from {source_path}.")