from datetime import datetime, timezone


def get_current_dt_utc() -> datetime:
    dt = datetime.now(tz=timezone.utc)
    return dt.replace(tzinfo=None)
