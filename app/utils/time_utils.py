from datetime import datetime, timedelta, timezone

UTC_PLUS_7 = timezone(timedelta(hours=7))


def now_utc7() -> datetime:
    return datetime.now(UTC_PLUS_7)


def now_iso_utc7() -> str:
    return now_utc7().strftime("%Y-%m-%d %H:%M:%S")


def today_utc7() -> str:
    return now_utc7().strftime("%Y-%m-%d")
