from datetime import datetime
from zoneinfo import ZoneInfo


def now() -> str:
    return datetime.now(ZoneInfo('Asia/Tokyo')).isoformat(timespec='seconds')


class AppError(Exception):
    def __init__(self, code: str, message: str, status: int = 400, field_errors: dict[str, str] | None = None):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status
        self.field_errors = field_errors
