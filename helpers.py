import asyncio
import base64
import binascii
from collections.abc import Iterable

from pyrogram.enums import ChatMemberStatus, ParseMode
from pyrogram.errors import FloodWait, UserNotParticipant

from config import LOGGER, SETTINGS


def encode_file_ids(message_ids: Iterable[int]) -> str:
    payload = "files:" + ",".join(str(message_id) for message_id in message_ids)
    return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")


def decode_file_ids(payload: str) -> list[int]:
    try:
        padded = payload + "=" * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode(padded.encode()).decode()
        prefix, raw_ids = decoded.split(":", 1)
        if prefix != "files":
            raise ValueError("Unexpected share payload")
        ids = [int(value) for value in raw_ids.split(",")]
        if not ids or any(message_id <= 0 for message_id in ids):
            raise ValueError("Invalid message ID")
        return ids
    except (ValueError, UnicodeDecodeError, binascii.Error) as error:
        raise ValueError("Invalid or corrupt file share link") from error


async def is_channel_member(client, channel_id: int, user_id: int) -> bool:
    try:
        member = await client.get_chat_member(channel_id, user_id)
        return member.status in {
            ChatMemberStatus.OWNER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.RESTRICTED,
        }
    except UserNotParticipant:
        return False
    except Exception as error:
        LOGGER.warning("Unable to verify channel %s membership for %s: %s", channel_id, user_id, error)
        return False


async def missing_required_channel_ids(client, user_id: int) -> tuple[int, ...]:
    """Only the first channel gates access to files."""
    channel_id = SETTINGS.force_sub_channel_id
    return () if await is_channel_member(client, channel_id, user_id) else (channel_id,)


async def deliver_file_ids(client, user_id: int, message_ids: list[int]) -> bool:
    """Copy storage-channel messages. Return True only if every copy succeeds."""
    all_sent = True
    for message_id in message_ids:
        try:
            message = await client.get_messages(SETTINGS.storage_channel_id, message_id)
            if not message or message.empty:
                all_sent = False
                continue
            await message.copy(user_id, parse_mode=ParseMode.HTML)
        except FloodWait as error:
            await asyncio.sleep(error.value)
            try:
                message = await client.get_messages(SETTINGS.storage_channel_id, message_id)
                await message.copy(user_id, parse_mode=ParseMode.HTML)
            except Exception as retry_error:
                LOGGER.warning("Could not deliver message %s to %s: %s", message_id, user_id, retry_error)
                all_sent = False
        except Exception as error:
            LOGGER.warning("Could not deliver message %s to %s: %s", message_id, user_id, error)
            all_sent = False
    return all_sent
