import asyncio

from pyrogram import filters
from pyrogram.errors import RPCError
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot import RequestJoinBot
from config import LOGGER, SETTINGS
from helpers import decode_file_ids, deliver_file_ids, missing_required_channel_ids


def _share_url(bot: RequestJoinBot, payload: str) -> str:
    return f"https://t.me/{bot.username}?start={payload}"


async def _persistent_join_link(bot: RequestJoinBot, channel_id: int) -> str:
    """Return the single saved request-to-join link for a channel."""
    async def create_link() -> str:
        invite = await bot.create_chat_invite_link(
            chat_id=channel_id,
            name=f"request-join-file-bot-{channel_id}",
            creates_join_request=True,
        )
        return invite.invite_link

    return await bot.db.get_or_create_join_request_link(channel_id, create_link)


async def _join_buttons(bot: RequestJoinBot, payload: str) -> InlineKeyboardMarkup:
    join_link = await _persistent_join_link(bot, SETTINGS.force_sub_channel_id)
    join_row = [InlineKeyboardButton("Join Channel 1 ↗", url=join_link)]
    if SETTINGS.dummy_button_link:
        join_row.append(
            InlineKeyboardButton(SETTINGS.dummy_button_text, url=SETTINGS.dummy_button_link)
        )
    buttons = [join_row]
    buttons.append([InlineKeyboardButton("Retry after joining", url=_share_url(bot, payload))])
    return InlineKeyboardMarkup(buttons)


@RequestJoinBot.on_message(filters.command("start") & filters.private)
async def start_command(bot: RequestJoinBot, message: Message) -> None:
    user = message.from_user
    if not user:
        return
    bot.db.add_user(user.id)

    payload = message.command[1] if len(message.command) > 1 else None
    if not payload:
        await message.reply_text(
            SETTINGS.start_message.format(first_name=user.first_name, first=user.first_name)
        )
        return

    try:
        file_ids = decode_file_ids(payload)
    except ValueError:
        await message.reply_text("That file link is invalid or has been damaged.")
        return

    missing_channel_ids = await missing_required_channel_ids(bot, user.id)
    if not missing_channel_ids:
        await deliver_file_ids(bot, user.id, file_ids)
        return

    bot.db.save_pending_file(user.id, payload)
    try:
        buttons = await _join_buttons(bot, payload)
    except Exception:
        LOGGER.exception("Could not create or retrieve the request-to-join link")
        await message.reply_text(
            "A required channel is temporarily unavailable. Please contact the administrator."
        )
        return

    first_name = user.first_name or "there"
    await message.reply_text(
        f"Hello {first_name} {SETTINGS.force_sub_message}",
        reply_markup=buttons,
    )


@RequestJoinBot.on_chat_join_request(filters.chat([SETTINGS.force_sub_channel_id]))
async def joined_by_request(bot: RequestJoinBot, join_request) -> None:
    """Approve automatically, then deliver after Channel 1 membership is verified."""
    user_id = join_request.from_user.id
    if not SETTINGS.auto_approve_join_requests:
        try:
            await bot.send_message(
                user_id,
                "Your request was recorded. Once a channel administrator approves it, open the file link again or tap Retry.",
            )
        except RPCError:
            pass
        return

    try:
        await bot.approve_chat_join_request(join_request.chat.id, user_id)
        # Telegram needs a short moment to expose the new membership to getChatMember.
        await asyncio.sleep(1)
        pending_payload = bot.db.get_pending_file(user_id)
        if not pending_payload or await missing_required_channel_ids(bot, user_id):
            return
        delivered = await deliver_file_ids(bot, user_id, decode_file_ids(pending_payload))
        if delivered:
            bot.db.clear_pending_file(user_id)
    except Exception as error:
        LOGGER.warning("Could not process join request for %s: %s", user_id, error)
