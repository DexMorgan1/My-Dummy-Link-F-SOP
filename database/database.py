import asyncio
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable
from uuid import uuid4

from pymongo import MongoClient, ReturnDocument


INVITE_KEY_PREFIX = "force_subscribe_invite:"


class Database:
    """MongoDB persistence for users, pending shares, and durable invite URLs."""

    def __init__(self, uri: str, database_name: str) -> None:
        self.client = MongoClient(uri, serverSelectionTimeoutMS=10_000)
        database = self.client[database_name]
        self.users = database["users"]
        self.pending_files = database["pending_files"]
        self.settings = database["bot_settings"]

    def check_connection(self) -> None:
        self.client.admin.command("ping")

    def add_user(self, user_id: int) -> None:
        self.users.update_one({"_id": user_id}, {"$setOnInsert": {"created_at": datetime.now(timezone.utc)}}, upsert=True)

    def user_ids(self) -> list[int]:
        return [record["_id"] for record in self.users.find({}, {"_id": 1})]

    def remove_user(self, user_id: int) -> None:
        self.users.delete_one({"_id": user_id})

    def save_pending_file(self, user_id: int, payload: str) -> None:
        self.pending_files.update_one(
            {"_id": user_id},
            {"$set": {"payload": payload, "created_at": datetime.now(timezone.utc)}},
            upsert=True,
        )

    def get_pending_file(self, user_id: int) -> str | None:
        record = self.pending_files.find_one({"_id": user_id}, {"payload": 1})
        return record["payload"] if record else None

    def clear_pending_file(self, user_id: int) -> None:
        self.pending_files.delete_one({"_id": user_id})

    async def get_or_create_join_request_link(
        self,
        channel_id: int,
        create_link: Callable[[], Awaitable[str]],
    ) -> str:
        """Return one durable join-request link per channel, even concurrently.

        MongoDB stores a short lease while Telegram creates the first link. A
        second bot process waits for the winner's saved URL instead of creating
        another link.
        """
        setting_id = f"{INVITE_KEY_PREFIX}{channel_id}"
        self.settings.update_one(
            {"_id": setting_id},
            {"$setOnInsert": {"channel_id": channel_id, "invite_link": None}},
            upsert=True,
        )

        while True:
            record = self.settings.find_one({"_id": setting_id}) or {}
            if record.get("invite_link"):
                return record["invite_link"]

            now = datetime.now(timezone.utc)
            token = uuid4().hex
            claimed = self.settings.find_one_and_update(
                {
                    "_id": setting_id,
                    "invite_link": None,
                    "$or": [
                        {"creation_lock_until": {"$exists": False}},
                        {"creation_lock_until": {"$lt": now}},
                    ],
                },
                {"$set": {"creation_token": token, "creation_lock_until": now + timedelta(minutes=2)}},
                return_document=ReturnDocument.AFTER,
            )
            if not claimed:
                await asyncio.sleep(0.25)
                continue

            try:
                invite_url = await create_link()
            except Exception:
                self.settings.update_one(
                    {"_id": setting_id, "creation_token": token},
                    {"$unset": {"creation_token": "", "creation_lock_until": ""}},
                )
                raise

            saved = self.settings.update_one(
                {"_id": setting_id, "creation_token": token},
                {
                    "$set": {"invite_link": invite_url, "created_at": datetime.now(timezone.utc)},
                    "$unset": {"creation_token": "", "creation_lock_until": ""},
                },
            )
            if saved.modified_count:
                return invite_url
