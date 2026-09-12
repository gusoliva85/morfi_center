from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from app.core.config import settings

UTC = ZoneInfo("UTC")


def now_utc() -> datetime:
    return datetime.now(UTC)


def to_local(dt: datetime) -> datetime:
    """Convierte un datetime a APP_TIMEZONE. Si es naive, se asume que ya está en UTC."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(ZoneInfo(settings.app_timezone))


def resolve_shift_instant(service_date: date | str, hhmm: str) -> datetime:
    """Convierte una fecha ('YYYY-MM-DD' o date) + hora de pared local ('HH:MM')
    en APP_TIMEZONE a un instante absoluto en UTC."""
    if isinstance(service_date, str):
        service_date = date.fromisoformat(service_date)
    hour, minute = (int(part) for part in hhmm.split(":"))
    local_dt = datetime.combine(
        service_date, time(hour, minute), tzinfo=ZoneInfo(settings.app_timezone)
    )
    return local_dt.astimezone(UTC)
