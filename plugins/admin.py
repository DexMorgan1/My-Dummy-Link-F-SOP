import asyncio

from pyrogram import filters
from pyrogram.errors import FloodWait, InputUserDeactivated, UserIsBlocked
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot import RequestJoinBot
from config import LOGGER, SETTINGS
from helpers import encode_file_ids


def _share_url(bot: RequestJoinBot, message_id: int) -> str:
    payload = encode_file_ids([message_id])
    return f"https://t.me/{bot.username}?start={payload}"


@RequestJoinBot.on_message(filters.private & filters.user(list(SETTINGS.admin_ids)) & ~filters.regex(r"^/"))
async def store_admin_message(bot: RequestJoinBot, message: Message) -> None:
    """Copy an administrator's message to storage and return its share URL."""
    try:
        stored = await message.copy(SETTINGS.storage_channel_id, disable_notification=True)
        link = _share_url(bot, stored.id)
        await message.reply_text(
            f"<b>Share link</b>\n\n{link}",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Share URL", url=f"https://t.me/share/url?url={link}")]]
            ),
            disable_web_page_preview=True,
        )
    except Exception as error:
        LOGGER.warning("Unable to store administrator message: %s", error)
        await message.reply_text("I could not store that message. Check storage-channel permissions.")


@RequestJoinBot.on_message(filters.command("users") & filters.private & filters.user(list(SETTINGS.admin_ids)))
async def users_command(bot: RequestJoinBot, message: Message) -> None:
    await message.reply_text(f"{len(bot.db.user_ids())} users have started the bot.")


@RequestJoinBot.on_message(filters.command("broadcast") & filters.private & filters.user(list(SETTINGS.admin_ids)))
async def broadcast_command(bot: RequestJoinBot, message: Message) -> None:
    if not message.reply_to_message:
        await message.reply_text("Reply to a message with /broadcast.")
        return

    delivered = 0
    for user_id in bot.db.user_ids():
        try:
            await message.reply_to_message.copy(user_id)
            delivered += 1
        except FloodWait as error:
            await asyncio.sleep(error.value)
        except (UserIsBlocked, InputUserDeactivated):
            bot.db.remove_user(user_id)
        except Exception as error:
            LOGGER.info("Broadcast to %s failed: %s", user_id, error)
    await message.reply_text(f"Broadcast complete: {delivered} delivered.")


@RequestJoinBot.on_message(filters.command("id") & filters.private)
async def id_command(_: RequestJoinBot, message: Message) -> None:
    await message.reply_text(f"Your Telegram user ID is <code>{message.chat.id}</code>.")
