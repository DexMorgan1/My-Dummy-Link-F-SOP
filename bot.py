from pyrogram import Client, utils
from pyrogram.enums import ParseMode

from config import SETTINGS
from database import Database


# Pyrogram is archived and still uses its former 32-bit channel-ID floor.
# Telegram now issues larger channel IDs (for example, -1004481963328), so
# widen the classifier before the client resolves configured channels.
utils.MIN_CHANNEL_ID = -100999999999999


class RequestJoinBot(Client):
    def __init__(self) -> None:
        super().__init__(
            name="request_join_file_bot",
            api_id=SETTINGS.api_id,
            api_hash=SETTINGS.api_hash,
            bot_token=SETTINGS.bot_token,
            plugins={"root": "plugins"},
            workers=4,
        )
        self.db = Database(SETTINGS.mongodb_uri, SETTINGS.mongodb_db)
        self.username = ""

    async def start(self) -> None:
        self.db.check_connection()
        await super().start()
        me = await self.get_me()
        self.username = me.username or ""
        self.set_parse_mode(ParseMode.HTML)

        # Fail early if the bot is not an administrator in its storage channel.
        probe = await self.send_message(SETTINGS.storage_channel_id, "Storage-channel permission check.")
        await probe.delete()
