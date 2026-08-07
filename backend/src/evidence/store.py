"""Phase 4 evidence-graph persistence, backed by MySQL (same database as
Phase 3 memory -- reuses MYSQL_* env vars). Tables are created
non-destructively (create_all) and never touch Phase 1/3 tables.

Follows the exact fault-tolerance pattern used by
src/memory/mysql_store.py: if MySQL is unreachable, everything degrades to a
volatile in-memory fallback so a research run never crashes because the
evidence graph couldn't be persisted.
"""

import os
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.types import Float, Integer, String, Text

from src.models.evidence import (
    Claim,
    ClaimStatus,
    Evidence,
    EvidenceRelationship,
    EvidenceType,
    NodeType,
    RelationshipType,
)


class Base(DeclarativeBase):
    pass


class ClaimRecord(Base):
    __tablename__ = "everso_claims"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    research_run_id: Mapped[str] = mapped_column(String(64), index=True)
    claim_text: Mapped[str] = mapped_column(Text)
    normalized_claim: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    importance: Mapped[float] = mapped_column(Float, default=0.5)
    status: Mapped[str] = mapped_column(String(32), default=ClaimStatus.UNVERIFIED.value)
    supporting_count: Mapped[int] = mapped_column(Integer, default=0)
    contradicting_count: Mapped[int] = mapped_column(Integer, default=0)
    source_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[str] = mapped_column(String(64))
    updated_at: Mapped[str] = mapped_column(String(64))

    def to_model(self) -> Claim:
        return Claim(
            id=self.id,
            research_run_id=self.research_run_id,
            claim_text=self.claim_text,
            normalized_claim=self.normalized_claim or "",
            confidence=float(self.confidence),
            importance=float(self.importance),
            status=ClaimStatus(self.status),
            supporting_count=int(self.supporting_count),
            contradicting_count=int(self.contradicting_count),
            source_count=int(self.source_count),
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class EvidenceRecordRow(Base):
    __tablename__ = "everso_evidence"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    research_run_id: Mapped[str] = mapped_column(String(64), index=True)
    claim_id: Mapped[str] = mapped_column(String(64), index=True)
    source_id: Mapped[str] = mapped_column(String(64), index=True)
    evidence_text: Mapped[str] = mapped_column(Text)
    evidence_type: Mapped[str] = mapped_column(String(32), default=EvidenceType.CONTEXTUAL.value)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    created_at: Mapped[str] = mapped_column(String(64))

    def to_model(self) -> Evidence:
        return Evidence(
            id=self.id,
            research_run_id=self.research_run_id,
            claim_id=self.claim_id,
            source_id=self.source_id,
            evidence_text=self.evidence_text,
            evidence_type=EvidenceType(self.evidence_type),
            confidence=float(self.confidence),
            created_at=self.created_at,
        )


class RelationshipRecord(Base):
    __tablename__ = "everso_evidence_relationships"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    research_run_id: Mapped[str] = mapped_column(String(64), index=True)
    from_type: Mapped[str] = mapped_column(String(16))
    from_id: Mapped[str] = mapped_column(String(64), index=True)
    relationship_type: Mapped[str] = mapped_column(String(16))
    to_type: Mapped[str] = mapped_column(String(16))
    to_id: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[str] = mapped_column(String(64))

    def to_model(self) -> EvidenceRelationship:
        return EvidenceRelationship(
            id=self.id,
            research_run_id=self.research_run_id,
            from_type=NodeType(self.from_type),
            from_id=self.from_id,
            relationship_type=RelationshipType(self.relationship_type),
            to_type=NodeType(self.to_type),
            to_id=self.to_id,
            created_at=self.created_at,
        )


def _env(key: str, default: Any = None) -> Any:
    return os.getenv(key, default)


class EvidenceStore:
    """Claim/Evidence/Relationship persistence. MySQL primary, in-memory
    fallback for degraded mode -- mirrors src/memory/mysql_store.py."""

    def __init__(self, engine: Optional[Engine] = None, create_tables: bool = True):
        self._mysql_active = False
        self._engine: Optional[Engine] = None
        self._session: Optional[sessionmaker] = None

        self._fallback_claims: Dict[str, Claim] = {}
        self._fallback_evidence: Dict[str, Evidence] = {}
        self._fallback_relationships: Dict[str, EvidenceRelationship] = {}

        if engine is None:
            engine = self._build_engine_from_env()
        self._try_connect(engine, create_tables)

    def _build_engine_from_env(self) -> Optional[Engine]:
        host = _env("MYSQL_HOST")
        port = _env("MYSQL_PORT", "3306")
        user = _env("MYSQL_USER")
        password = _env("MYSQL_PASSWORD")
        database = _env("MYSQL_DATABASE")
        if not (host and user and database):
            return None
        try:
            return create_engine(
                f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}",
                pool_pre_ping=True,
                pool_recycle=3600,
                connect_args={"connect_timeout": 3},
            )
        except Exception:
            return None

    def _try_connect(self, engine: Optional[Engine], create_tables: bool):
        if engine is None:
            return
        try:
            from sqlalchemy import text as sa_text

            with engine.connect() as conn:
                conn.execute(sa_text("SELECT 1"))
            if create_tables:
                Base.metadata.create_all(engine)
            self._engine = engine
            self._session = sessionmaker(bind=engine)
            self._mysql_active = True
        except Exception:
            self._mysql_active = False

    @property
    def is_mysql_active(self) -> bool:
        return self._mysql_active

    def ping(self) -> bool:
        return self._mysql_active

    # -- claims --------------------------------------------------------
    def save_claim(self, claim: Claim) -> Claim:
        if self._mysql_active:
            try:
                with self._session() as session:
                    session.merge(ClaimRecord(
                        id=claim.id, research_run_id=claim.research_run_id,
                        claim_text=claim.claim_text, normalized_claim=claim.normalized_claim,
                        confidence=claim.confidence, importance=claim.importance,
                        status=claim.status.value, supporting_count=claim.supporting_count,
                        contradicting_count=claim.contradicting_count, source_count=claim.source_count,
                        created_at=claim.created_at, updated_at=claim.updated_at,
                    ))
                    session.commit()
                return claim
            except Exception:
                pass
        self._fallback_claims[claim.id] = claim.model_copy()
        return claim

    def get_claim(self, claim_id: str) -> Optional[Claim]:
        if self._mysql_active:
            try:
                with self._session() as session:
                    record = session.get(ClaimRecord, claim_id)
                    return record.to_model() if record else None
            except Exception:
                pass
        return self._fallback_claims.get(claim_id)

    def list_claims_by_run(self, research_run_id: str) -> List[Claim]:
        if self._mysql_active:
            try:
                with self._session() as session:
                    records = (
                        session.query(ClaimRecord)
                        .filter(ClaimRecord.research_run_id == research_run_id)
                        .all()
                    )
                    return [r.to_model() for r in records]
            except Exception:
                pass
        return [c for c in self._fallback_claims.values() if c.research_run_id == research_run_id]

    # -- evidence --------------------------------------------------------
    def save_evidence(self, evidence: Evidence) -> Evidence:
        if self._mysql_active:
            try:
                with self._session() as session:
                    session.merge(EvidenceRecordRow(
                        id=evidence.id, research_run_id=evidence.research_run_id,
                        claim_id=evidence.claim_id, source_id=evidence.source_id,
                        evidence_text=evidence.evidence_text, evidence_type=evidence.evidence_type.value,
                        confidence=evidence.confidence, created_at=evidence.created_at,
                    ))
                    session.commit()
                return evidence
            except Exception:
                pass
        self._fallback_evidence[evidence.id] = evidence.model_copy()
        return evidence

    def list_evidence_by_claim(self, claim_id: str) -> List[Evidence]:
        if self._mysql_active:
            try:
                with self._session() as session:
                    records = (
                        session.query(EvidenceRecordRow)
                        .filter(EvidenceRecordRow.claim_id == claim_id)
                        .all()
                    )
                    return [r.to_model() for r in records]
            except Exception:
                pass
        return [e for e in self._fallback_evidence.values() if e.claim_id == claim_id]

    def list_evidence_by_run(self, research_run_id: str) -> List[Evidence]:
        if self._mysql_active:
            try:
                with self._session() as session:
                    records = (
                        session.query(EvidenceRecordRow)
                        .filter(EvidenceRecordRow.research_run_id == research_run_id)
                        .all()
                    )
                    return [r.to_model() for r in records]
            except Exception:
                pass
        return [e for e in self._fallback_evidence.values() if e.research_run_id == research_run_id]

    # -- relationships -----------------------------------------------------
    def save_relationship(self, rel: EvidenceRelationship) -> EvidenceRelationship:
        if self._mysql_active:
            try:
                with self._session() as session:
                    session.merge(RelationshipRecord(
                        id=rel.id, research_run_id=rel.research_run_id,
                        from_type=rel.from_type.value, from_id=rel.from_id,
                        relationship_type=rel.relationship_type.value,
                        to_type=rel.to_type.value, to_id=rel.to_id,
                        created_at=rel.created_at,
                    ))
                    session.commit()
                return rel
            except Exception:
                pass
        self._fallback_relationships[rel.id] = rel.model_copy()
        return rel

    def list_relationships_by_run(self, research_run_id: str) -> List[EvidenceRelationship]:
        if self._mysql_active:
            try:
                with self._session() as session:
                    records = (
                        session.query(RelationshipRecord)
                        .filter(RelationshipRecord.research_run_id == research_run_id)
                        .all()
                    )
                    return [r.to_model() for r in records]
            except Exception:
                pass
        return [r for r in self._fallback_relationships.values() if r.research_run_id == research_run_id]

    def list_relationships_from(self, from_id: str) -> List[EvidenceRelationship]:
        if self._mysql_active:
            try:
                with self._session() as session:
                    records = (
                        session.query(RelationshipRecord)
                        .filter(RelationshipRecord.from_id == from_id)
                        .all()
                    )
                    return [r.to_model() for r in records]
            except Exception:
                pass
        return [r for r in self._fallback_relationships.values() if r.from_id == from_id]

    def get_contradictions_for_claim(self, claim_id: str) -> List[Evidence]:
        rels = [
            r for r in self.list_relationships_from(claim_id)
            if r.relationship_type == RelationshipType.CONTRADICTS
        ]
        contradicting_ids = {r.to_id for r in rels}
        return [e for e in self.list_evidence_by_claim(claim_id) if e.id in contradicting_ids]


_evidence_store: Optional[EvidenceStore] = None


def get_evidence_store() -> EvidenceStore:
    global _evidence_store
    if _evidence_store is None:
        _evidence_store = EvidenceStore()
    return _evidence_store
