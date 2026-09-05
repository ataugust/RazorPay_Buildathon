"""Clear transactional ASC data while preserving catalog and merchant policy."""

import argparse

from sqlalchemy import delete

from app.db.models.agent_message import AgentMessage
from app.db.models.audit_event import AuditEvent
from app.db.models.deal import Deal
from app.db.session import SessionLocal


def reset_transaction_data() -> None:
    with SessionLocal() as db:
        db.execute(delete(AgentMessage))
        db.execute(delete(AuditEvent))
        db.execute(delete(Deal))
        db.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm", action="store_true", help="Confirm destructive transaction reset")
    args = parser.parse_args()
    if not args.confirm:
        raise SystemExit("Refusing to clear data without --confirm")
    reset_transaction_data()
    print("Transaction reset complete: deals, agent messages, and audit events cleared.")
