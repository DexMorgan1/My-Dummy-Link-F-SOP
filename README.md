# Request-Join File Bot

A Telegram file-sharing bot with one required **request-to-join** channel and
one configurable link button.

An admin sends a file to the bot. The bot copies it to a private storage
channel and returns a share link. When a visitor opens that share link, they
must request to join the required channel before receiving the file.

## One shared request link

The bot creates one request-to-join link for `FORCE_SUB_CHANNEL_1`, saves it in
MongoDB, and reuses it for every visitor and after restarts. The second button
uses `DUMMY_BUTTON_LINK`. Visitors do not have to join or open that link to
receive a file.

## User flow

1. An administrator sends a file or message to the bot in a private chat.
2. The bot copies it to `CHANNEL_ID` and returns a private share URL.
3. A visitor opens the share URL.
4. If they are not a member of `FORCE_SUB_CHANNEL_1`, the bot shows its saved
   request-to-join link, the optional `DUMMY_BUTTON_LINK` beside it, and a Retry
   button below them.
5. With `AUTO_APPROVE_JOIN_REQUESTS=True`, the bot approves the request and
   automatically sends the file once channel membership is verified. Set it to
   `False` if a human administrator should approve requests; those users can
   use Retry once accepted.

## Before running

Create two Telegram channels:

- A private **storage channel**, set as `CHANNEL_ID`. The bot must be an
  administrator and able to post/delete messages.
- One private **required channel**, set as `FORCE_SUB_CHANNEL_1`. The bot must
  be an administrator there with permission to invite users and approve join
  requests.

Create a MongoDB database, copy `.env.example` to `.env`, and populate every
required value. Never commit `.env`.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export $(grep -v '^#' .env | xargs)
python main.py
```

## Commands

- `/start` — welcome message, or retrieve the file in a share URL.
- `/id` — show your Telegram user ID.
- `/users` — administrator-only user count.
- `/broadcast` — administrator-only; reply to a message with this command.

Administrators can send any non-command message to the bot to store it and
receive a share URL.

## Configuration

See `.env.example`. `ADMINS` is a space-separated list of numeric Telegram
user IDs. `OWNER_ID` is automatically treated as an administrator too.

For compatibility with the original project, `APP_ID`, `TG_BOT_TOKEN`,
`DATABASE_URL`, `DATABASE_NAME`, and `FORCE_SUB_CHANNEL` are also accepted.
`FORCE_SUB_CHANNEL_2` and `FORCE_SUB_CHANNEL2` are ignored. Set
`DUMMY_BUTTON_LINK` in Railway to a full URL such as `https://t.me/example`.
Optionally set `DUMMY_BUTTON_TEXT` (default: `Join Channel 2`). If the link is
empty, the second button is hidden. `FORCE_SUB_MESSAGE` controls the message
above the buttons.

The bundled compatibility shim supports modern Telegram channel IDs beyond
Pyrogram's old 32-bit channel-ID range.

## Railway

Railway detects the included `Dockerfile` and runs `python main.py`. Add the
values from `.env.example` in the Railway service's **Variables** tab; do not
upload an `.env` file. The bot is a worker, so it does not need a public domain
or a `PORT` variable.

## Credits and license

This is a clean, focused implementation of the file-store pattern inspired by
[Codeflix FileStore](https://github.com/Codeflix-Bots/FileStore), the upstream
project behind the repository supplied for this request. It is distributed
under GPL-3.0-or-later; see `LICENSE` and retain the notice when redistributing
modified versions.
