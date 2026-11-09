---
name: instagram-reel-bot
description: Set up a personal Instagram DM bot that analyzes shared reels, posts and carousels with Claude and replies in the same chat. Use when someone wants to share Instagram reels/posts to a bot account and get Claude's explanation back, on Windows, with a Meta developer app, webhooks, a local Python server and a fixed ngrok link.
---

# Instagram Reel Bot setup

The user shares a reel or post to a private bot account on Instagram. A small Python server on their PC receives it through Meta's webhook, downloads the video or slides, extracts frames and transcribes the audio, asks Claude, and replies in the same Instagram chat.

The code is in the `bot/` folder next to this file. The full Arabic walkthrough is in `STEPS-AR.txt`, and how to install this kit is in `INSTALL-AR.txt`.

## How to guide the user

- Go one step at a time and wait for confirmation (screenshot or "done") before the next step. Meta's dashboard changes often: read their screenshots and point to what is actually on screen.
- Never ask the user to paste a secret (tokens, app secret, API keys, cookies) into the chat. Secrets go into `.env` only, through `setup-env.ps1` / `update-token.ps1`, which hide input.
- Commands for the user go in separate code blocks, with nothing extra around them.

## Steps

1. **Bot account.** Create a second Instagram account. Switch it to Professional → Creator. Follow it from the personal account. In the bot account: Settings → Messages and story replies → Message requests → Connected tools → turn on "Allow access to messages".
2. **Meta app.** At developers.facebook.com create an app with the use case "Manage messaging & content on Instagram". Open **API setup with Instagram login** (not the Facebook login one). Click "Add all required permissions".
3. **Testers.** App roles → Roles → Add people → Instagram Tester: add the bot account and the user's personal account. Accept both invites at instagram.com/accounts/manage_access (Tester invites tab), logged into each account.
4. **Install on Windows.** Python 3.12+, then:
   - `winget install Gyan.FFmpeg`
   - `winget install ngrok.ngrok` then `ngrok update` (old versions are rejected)
   - Unzip `bot/` to e.g. `C:\Users\<you>\projects\reel-bot`, then `python -m venv .venv`, `.venv\Scripts\activate`, `pip install -r requirements.txt`
5. **Secrets.** In Meta step 2 "Generate access tokens" → Add account (bot) → Generate token. Copy the Instagram app secret (box at the top, "Show"). Get a Claude API key from console.anthropic.com. Run `.\setup-env.ps1` and paste each one (leave verify token empty to auto-generate; note the printed value).
6. **Fixed link.** Free ngrok account → dashboard → Domains: copy the free static domain. Run `ngrok config add-authtoken <token>` with the token from the dashboard. Run `.\install-autostart.ps1` (asks for the domain). It starts the server and tunnel hidden, at every Windows login, restarting them if they stop. Logs are in `logs\`.
7. **Webhook.** Meta → API setup with Instagram login → step 3 Webhooks: Callback URL `https://<domain>/webhook`, Verify token = the one from step 5, Verify and save. Subscribe to the `messages` field. Run `python subscribe.py` (should print `success: true` and `messages`).
8. **Publish the app.** Host `bot/privacy/index.html` anywhere public (e.g. Netlify Drop) after putting a contact email in it. App settings → Basic: Privacy policy URL, Terms URL and User data deletion URL = that page, Category = Messaging, Save. Run `python test_calls.py` once (Meta wants each permission used before it shows Publish). Then Publish → Publish. Real DMs are only delivered after publishing.
9. **Lock to the owner.** Send the bot "hello" from the personal account. The bot replies with a setup hint containing your number (also logged as `Sender id: <number>` in `logs\server-errors.log`). Put it in `.env` as `ALLOWED_SENDER_ID=<number>`, then `.\stop-bot.ps1` and `.\install-autostart.ps1`.
10. **Cookie for carousels and blocked reels.** In Chrome, log into Instagram with the bot account, install the "Get cookies.txt LOCALLY" extension, open instagram.com, click the extension → Export. Rename to `cookies.txt` and put it in the bot folder. Treat it like a password. Re-export when links stop working (it expires or logs out).
11. **Optional.** Copy `data/projects.md.example` to `data/projects.md` and list the user's projects, so verdicts say which project a reel helps. Set `HISTORY_KEY` in `.env` to a random string for a live history page at `https://<domain>/history?k=<key>`.

## Using it

- **Reel:** share it to the bot account. Reply in 20–60 seconds.
- **Carousel post:** Instagram's share only sends the first slide. Copy the post's link and paste it in the chat (needs `cookies.txt`), or send screenshots of all slides at once: the bot reads them together.
- **Commands:** `/reset` new conversation, `/reels` saved summaries, `/help`.

## Troubleshooting

- **Only "read" events arrive, no messages:** the app is not published, or "Allow access to messages" is off on the bot account, or the access token was created before permissions were added (generate a new one and run `.\update-token.ps1`).
- **No Publish button:** run `python test_calls.py`, wait a few minutes, reload the Publish page.
- **Tunnel keeps restarting:** check `logs\tunnel-errors.log`; usually `ngrok update` or a wrong domain.
- **"Instagram blocked the video download" / gallery-dl redirects to login:** export a fresh `cookies.txt`; also `.venv\Scripts\python -m pip install -U yt-dlp gallery-dl`.
- **Signature failed in logs:** `IG_APP_SECRET` is the Facebook app secret instead of the Instagram app secret.
