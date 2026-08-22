import json
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text
from typing import List, Dict, Any

class IngestService:
    def __init__(self, db_session, run_id: str):
        self.db = db_session
        self.run_id = run_id

    def ingest(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        accepted = 0
        deduplicated = 0
        rejected = 0
        rejected_reasons = []

        valid_sources = {"BANK", "INVOICE", "GATEWAY"}
        valid_lifecycles = {"INITIATED", "CAPTURED", "PARTIALLY_SETTLED", "SETTLED", "REFUNDED", "REVERSED", "FAILED"}

        for record in records:
            # 1. Pop ground_truth_group_id
            record.pop("ground_truth_group_id", None)
            
            # 2. Validate
            reason = None
            if record.get("source") not in valid_sources:
                reason = f"Invalid source: {record.get('source')}"
            elif record.get("lifecycle_state") not in valid_lifecycles:
                reason = f"Invalid lifecycle_state: {record.get('lifecycle_state')}"
            elif not isinstance(record.get("amount_minor_units"), int) or record.get("amount_minor_units") <= 0:
                reason = f"Invalid amount_minor_units: {record.get('amount_minor_units')}"
            elif not isinstance(record.get("currency"), str) or len(record.get("currency")) != 3:
                reason = f"Invalid currency: {record.get('currency')}"
            elif not record.get("transaction_date"):
                reason = "Missing transaction_date"
            
            if reason:
                rejected += 1
                rejected_reasons.append(reason)
                continue

            # 3. Attempt INSERT
            try:
                stmt = text('''
                    INSERT INTO source_records (
                        run_id, source, source_event_id, amount_minor_units, currency,
                        reference, counterparty, description, transaction_date, lifecycle_state, raw_payload
                    ) VALUES (
                        :run_id, :source, :source_event_id, :amount_minor_units, :currency,
                        :reference, :counterparty, :description, :transaction_date, :lifecycle_state, :raw_payload
                    )
                ''')
                self.db.execute(stmt, {
                    "run_id": self.run_id,
                    "source": record["source"],
                    "source_event_id": record["source_event_id"],
                    "amount_minor_units": record["amount_minor_units"],
                    "currency": record["currency"],
                    "reference": record.get("reference"),
                    "counterparty": record.get("counterparty"),
                    "description": record.get("description"),
                    "transaction_date": record["transaction_date"],
                    "lifecycle_state": record["lifecycle_state"],
                    "raw_payload": json.dumps(record.get("raw_payload", {}))
                })
                self.db.commit()
                accepted += 1
            except IntegrityError as e:
                self.db.rollback()
                # 3. On UniqueViolation (run_id, source, source_event_id): increment deduplicated, do not raise
                deduplicated += 1
            except Exception as e:
                self.db.rollback()
                rejected += 1
                rejected_reasons.append(str(e))

        # 5. Return counts
        return {
            "accepted": accepted,
            "deduplicated": deduplicated,
            "rejected": rejected,
            "rejected_reasons": rejected_reasons
        }
