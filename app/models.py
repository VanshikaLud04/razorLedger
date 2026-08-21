from sqlalchemy import Column, String, BigInteger, Boolean, Date, DateTime, ARRAY, Text, ForeignKey, text, func, Float
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship
from app.db import Base

class Run(Base):
    __tablename__ = 'runs'
    run_id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    dataset_seed = Column(Text, nullable=False)
    dataset_partition = Column(Text, nullable=False)
    matcher_version = Column(Text, nullable=False)
    embedding_model = Column(Text, nullable=False)
    llm_model = Column(Text, nullable=False)
    prompt_version = Column(Text, nullable=False)
    code_commit = Column(Text, nullable=False)
    run_cutoff_time = Column(DateTime(timezone=True), nullable=False)
    dataset_snapshot_hash = Column(Text, nullable=False)
    thresholds = Column(JSONB, nullable=False)
    status = Column(Text, nullable=False, server_default='RUNNING')
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at = Column(DateTime(timezone=True))

class SourceRecord(Base):
    __tablename__ = 'source_records'
    source_record_id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    run_id = Column(PG_UUID(as_uuid=True), ForeignKey('runs.run_id'), nullable=False)
    source = Column(Text, nullable=False)
    source_event_id = Column(Text, nullable=False)
    amount_minor_units = Column(BigInteger, nullable=False)
    currency = Column(String(3), nullable=False)
    reference = Column(Text)
    counterparty = Column(Text)
    description = Column(Text)
    transaction_date = Column(Date, nullable=False)
    lifecycle_state = Column(Text, nullable=False)
    raw_payload = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

class EconomicEvent(Base):
    __tablename__ = 'economic_events'
    economic_event_id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    run_id = Column(PG_UUID(as_uuid=True), ForeignKey('runs.run_id'), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

class EconomicEventLink(Base):
    __tablename__ = 'economic_event_links'
    economic_event_id = Column(PG_UUID(as_uuid=True), ForeignKey('economic_events.economic_event_id', ondelete='CASCADE'), primary_key=True)
    source_record_id = Column(PG_UUID(as_uuid=True), ForeignKey('source_records.source_record_id'), primary_key=True)
    role = Column(Text, nullable=False)

class Candidate(Base):
    __tablename__ = 'candidates'
    candidate_id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    run_id = Column(PG_UUID(as_uuid=True), ForeignKey('runs.run_id'), nullable=False)
    source_record_id = Column(PG_UUID(as_uuid=True), ForeignKey('source_records.source_record_id'), nullable=False)
    candidate_source_record_id = Column(PG_UUID(as_uuid=True), ForeignKey('source_records.source_record_id'), nullable=False)
    amount_agreement = Column(Boolean)
    amount_difference_bin = Column(Text)
    date_delta_bin = Column(Text)
    reference_similarity_bin = Column(Text)
    reference_similarity_score = Column(Float)
    counterparty_similarity_bin = Column(Text)
    counterparty_similarity_score = Column(Float)
    description_similarity_bin = Column(Text)
    semantic_similarity_score = Column(Float)
    source_compatibility = Column(Boolean)
    evidence_rarity_score = Column(Float)
    evidence_families_present = Column(ARRAY(Text))
    probabilistic_confidence = Column(Float)
    confidence_gap_to_next = Column(Float)
    llm_invoked = Column(Boolean, nullable=False, server_default=text('false'))
    llm_supporting_evidence = Column(JSONB)
    llm_contradicting_evidence = Column(JSONB)
    llm_semantic_assessment = Column(Text)
    llm_stated_uncertainty = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

class Decision(Base):
    __tablename__ = 'decisions'
    decision_id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    run_id = Column(PG_UUID(as_uuid=True), ForeignKey('runs.run_id'), nullable=False)
    source_record_id = Column(PG_UUID(as_uuid=True), ForeignKey('source_records.source_record_id'), nullable=False)
    chosen_candidate_id = Column(PG_UUID(as_uuid=True), ForeignKey('candidates.candidate_id'))
    action = Column(Text, nullable=False)
    primary_reason = Column(Text, nullable=False)
    control_result = Column(Text, nullable=False)
    risk_exposure_score = Column(Float)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

class Allocation(Base):
    __tablename__ = 'allocations'
    allocation_id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    run_id = Column(PG_UUID(as_uuid=True), ForeignKey('runs.run_id'), nullable=False)
    allocation_type = Column(Text, nullable=False)
    economic_event_id = Column(PG_UUID(as_uuid=True), ForeignKey('economic_events.economic_event_id'), nullable=False)
    total_amount_minor = Column(BigInteger, nullable=False)
    currency = Column(String(3), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

class AllocationLine(Base):
    __tablename__ = 'allocation_lines'
    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    allocation_id = Column(PG_UUID(as_uuid=True), ForeignKey('allocations.allocation_id', ondelete='CASCADE'), nullable=False)
    source_record_id = Column(PG_UUID(as_uuid=True), ForeignKey('source_records.source_record_id'), nullable=False)
    allocated_amount_minor = Column(BigInteger, nullable=False)
    currency = Column(String(3), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

class ControlResult(Base):
    __tablename__ = 'control_results'
    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    run_id = Column(PG_UUID(as_uuid=True), ForeignKey('runs.run_id'), nullable=False)
    control_id = Column(Text, nullable=False)
    status = Column(Text, nullable=False)
    message = Column(Text)
    related_entity_ids = Column(ARRAY(PG_UUID(as_uuid=True)))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

class AuditLog(Base):
    __tablename__ = 'audit_log'
    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    run_id = Column(PG_UUID(as_uuid=True), ForeignKey('runs.run_id'), nullable=False)
    entity_id = Column(PG_UUID(as_uuid=True), nullable=False)
    event_type = Column(Text, nullable=False)
    old_state = Column(Text)
    new_state = Column(Text)
    primary_reason = Column(Text)
    control_result = Column(Text)
    action = Column(Text)
    actor = Column(Text, nullable=False)
    matcher_version = Column(Text)
    prompt_version = Column(Text)
    previous_hash = Column(Text)
    current_hash = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

class ReviewQueue(Base):
    __tablename__ = 'review_queue'
    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    run_id = Column(PG_UUID(as_uuid=True), ForeignKey('runs.run_id'), nullable=False)
    decision_id = Column(PG_UUID(as_uuid=True), ForeignKey('decisions.decision_id'), nullable=False)
    status = Column(Text, nullable=False, server_default='OPEN')
    resolution_source = Column(Text)
    resolved_candidate_id = Column(PG_UUID(as_uuid=True), ForeignKey('candidates.candidate_id'))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    resolved_at = Column(DateTime(timezone=True))
