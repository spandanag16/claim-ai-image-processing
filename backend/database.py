"""SQLite persistence for generated claim analyses (synopsis: Database Integration).

SQLAlchemy + SQLite keeps the pricing/report data queryable without requiring
a MySQL server; the schema mirrors what a MySQL deployment would use.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import JSON, DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


BASE_DIR = Path(__file__).resolve().parent
DATABASE_URL = f"sqlite:///{BASE_DIR / 'claimai.db'}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


class Base(DeclarativeBase):
    pass


class ClaimAnalysis(Base):
    __tablename__ = "claim_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    claim_id: Mapped[str] = mapped_column(String(64), index=True)
    severity_label: Mapped[str] = mapped_column(String(16))
    severity_score: Mapped[float] = mapped_column(Float)
    estimated_cost: Mapped[float] = mapped_column(Float)
    report_json: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


def init_db() -> None:
    Base.metadata.create_all(engine)


def save_analysis(claim_id: str, report: dict) -> int:
    from sqlalchemy.orm import Session

    with Session(engine) as session:
        row = ClaimAnalysis(
            claim_id=claim_id,
            severity_label=report["severity"]["severity"],
            severity_score=report["severity"]["score"],
            estimated_cost=report["cost_estimate"]["estimated_repair_cost"],
            report_json=report,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return row.id


def get_analysis(claim_id: str) -> dict | None:
    from sqlalchemy.orm import Session

    with Session(engine) as session:
        row = (
            session.query(ClaimAnalysis)
            .filter(ClaimAnalysis.claim_id == claim_id)
            .order_by(ClaimAnalysis.id.desc())
            .first()
        )
        return json.loads(json.dumps(row.report_json)) if row else None
