import time


MAX_FAILED_ATTEMPTS = 5
BLOCK_DURATION = 15 * 60

failed_attempts: dict[str, dict] = {}


def is_ip_blocked(ip: str) -> bool:
    record = failed_attempts.get(ip)

    if not record:
        return False

    blocked_until = record.get("blocked_until")

    if blocked_until is None:
        return False

    if time.time() < blocked_until:
        return True

    # Block expired → reset
    failed_attempts.pop(ip, None)
    return False


def record_failed_attempt(ip: str):
    record = failed_attempts.setdefault(
        ip,
        {
            "attempts": 0,
            "blocked_until": None,
        },
    )

    record["attempts"] += 1

    if record["attempts"] >= MAX_FAILED_ATTEMPTS:
        record["blocked_until"] = time.time() + BLOCK_DURATION


def get_retry_after(ip: str) -> int:
    record = failed_attempts.get(ip)

    if not record or not record.get("blocked_until"):
        return 0

    remaining = record["blocked_until"] - time.time()

    return max(0, int(remaining))


def reset_ip(ip: str):
    failed_attempts.pop(ip, None)