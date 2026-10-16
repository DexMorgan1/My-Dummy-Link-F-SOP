import logging
import os
from dataclasses import dataclass


def _value(*names: str) -> str:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def _required(*names: str) -> str:
    value = _value(*names)
    if not value:
        raise RuntimeError(f"Set one of: {', '.join(names)}.")
    return value


def _int(*names: str, required: bool = True, default: int = 0) -> int:
    raw = _value(*names)
    if not raw:
        if required:
            raise RuntimeError(f"Set one of {', '.join(names)} to a numeric Telegram ID.")
        return default
    try:
        return int(raw)
    except ValueError as error:
        raise RuntimeError(f"{names[0]} must be numeric.") from error


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name, str(default)).strip().lower()
    if value not in {"true", "false"}:
        raise RuntimeError(f"{name} must be True or False.")
    return value == "true"


@dataclass(frozen=True)
class Settings:
    api_id: int
    api_hash: str
    bot_token: str
    storage_channel_id: int
    force_sub_channel_id: int
    dummy_button_link: str
    dummy_button_text: str
    mongodb_uri: str
    mongodb_db: str
    admin_ids: frozenset[int]
    auto_approve_join_requests: bool
    start_message: str
    force_sub_message: str


def load_settings() -> Settings:
    owner_id = _int("OWNER_ID", required=False)
    admin_ids = {
        int(value)
        for value in os.getenv("ADMINS", "").split()
        if value.strip()
    }
    if owner_id:
        admin_ids.add(owner_id)
    if not admin_ids:
        raise RuntimeError("Set OWNER_ID or at least one ADMINS value.")

    return Settings(
        api_id=_int("API_ID", "APP_ID"),
        api_hash=_required("API_HASH"),
        bot_token=_required("BOT_TOKEN", "TG_BOT_TOKEN"),
        storage_channel_id=_int("CHANNEL_ID"),
        force_sub_channel_id=_int("FORCE_SUB_CHANNEL_1", "FORCE_SUB_CHANNEL"),
        dummy_button_link=_value("DUMMY_BUTTON_LINK"),
        dummy_button_text=_value("DUMMY_BUTTON_TEXT") or "Join Channel 2 ↗",
        mongodb_uri=_required("MONGODB_URI", "DATABASE_URL"),
        mongodb_db=_value("MONGODB_DB", "DATABASE_NAME") or "request_join_file_bot",
        admin_ids=frozenset(admin_ids),
        auto_approve_join_requests=_bool("AUTO_APPROVE_JOIN_REQUESTS", True),
        start_message=os.getenv(
            "START_MESSAGE",
            "<b>Welcome, {first_name}.</b> Send me a file share link to retrieve a file.",
        ),
        force_sub_message=os.getenv(
            "FORCE_SUB_MESSAGE",
            "Please request to join our channel first.",
        ),
    )


SETTINGS = load_settings()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logging.getLogger("pyrogram").setLevel(logging.WARNING)
LOGGER = logging.getLogger("request_join_file_bot")
