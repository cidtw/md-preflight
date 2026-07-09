import argparse
from datetime import datetime, timedelta, UTC
import random
import sys
import uuid

from app.schemas.history import RunHistoryRecord, RuleTrigger
from app.schemas.issue import Severity
from app.services.history_store import build_history_store


def seed_database(user_ids: list[str]) -> None:
    history_store = build_history_store()
    store_type = type(history_store).__name__
    print(f"Using history store: {store_type}")

    if store_type == "InMemoryHistoryStore":
        print("Warning: Database URL is not configured. Seeding in-memory store will not persist.")

    now = datetime.now(UTC)

    rules_pool = [
        ("INVALID_DATE_RANGE", Severity.ERROR),
        ("MISSING_PRODUCT_MASTER", Severity.ERROR),
        ("INCOMPLETE_PRODUCT_MASTER", Severity.ERROR),
        ("INVALID_PROMO_PRICE", Severity.ERROR),
        ("EXTREME_DISCOUNT_RATE", Severity.WARNING),
        ("LOW_MARGIN_RATE", Severity.WARNING),
        ("DUPLICATE_MASTER_CODE", Severity.WARNING),
        ("INVENTORY_SHORTAGE_RISK", Severity.WARNING),
        ("INBOUND_DATE_CONFLICT", Severity.WARNING),
        ("MISSING_BENEFIT_CONDITION", Severity.ERROR),
    ]

    for user_id in user_ids:
        print(f"Seeding runs for user: {user_id}...")
        count = 0
        # Create 20 runs over the past 30 days
        for i in range(20):
            days_ago = i * 1.5 + random.uniform(0.1, 0.9)
            created_at = now - timedelta(days=days_ago)
            run_id = uuid.uuid4().hex

            passed = random.random() > 0.4
            if passed:
                error_count = 0
                warning_count = random.randint(0, 2)
                rules_triggered = []
                if warning_count > 0:
                    rules_triggered.append(
                        RuleTrigger(code="LOW_MARGIN_RATE", severity=Severity.WARNING, count=1)
                    )
                if warning_count > 1:
                    rules_triggered.append(
                        RuleTrigger(code="INVENTORY_SHORTAGE_RISK", severity=Severity.WARNING, count=1)
                    )
            else:
                error_count = random.randint(1, 3)
                warning_count = random.randint(0, 2)
                rules_triggered = []

                # Select unique random rules from pool
                selected_rules = random.sample(rules_pool, error_count + warning_count)
                errors_added = 0
                warnings_added = 0

                for code, severity in selected_rules:
                    if severity == Severity.ERROR and errors_added < error_count:
                        rules_triggered.append(
                            RuleTrigger(code=code, severity=Severity.ERROR, count=random.randint(1, 2))
                        )
                        errors_added += 1
                    elif severity == Severity.WARNING and warnings_added < warning_count:
                        rules_triggered.append(
                            RuleTrigger(code=code, severity=Severity.WARNING, count=random.randint(1, 3))
                        )
                        warnings_added += 1

            total_issues = sum(t.count for t in rules_triggered)
            # Re-adjust error/warning count based on rules_triggered
            actual_error_count = sum(t.count for t in rules_triggered if t.severity == Severity.ERROR)
            actual_warning_count = sum(t.count for t in rules_triggered if t.severity == Severity.WARNING)

            record = RunHistoryRecord(
                user_id=user_id,
                run_id=run_id,
                created_at=created_at,
                passed=passed,
                error_count=actual_error_count,
                warning_count=actual_warning_count,
                total_issues=total_issues,
                rules_triggered=rules_triggered,
                source_label="promotion_plan.csv",
            )
            history_store.append(record)
            count += 1

        print(f"Successfully seeded {count} runs for {user_id}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed run history database for MD Preflight.")
    parser.add_argument(
        "--user-id",
        type=str,
        nargs="+",
        default=["demo-user"],
        help="One or more user IDs to seed data for.",
    )
    args = parser.parse_args()

    seed_database(args.user_id)
