import asyncio
import re
import json
import os
from telethon import TelegramClient, events
from config import Config

# ---------------- STATE ----------------
possible = []
used_words = set()
last_guess = None
greens = {}
yellows = {}
grays = set()
game_active = False
CHAT_ID = None

client = TelegramClient("wordseek_session", Config.API_ID, Config.API_HASH)

# ---------------- SOLVER ----------------
def update_constraints(word, hint):
    local_present = set()
    local_greens = {}

    for i, sym in enumerate(hint):
        l = word[i]
        if sym == "🟩":
            local_greens[i] = l
            local_present.add(l)
        elif sym == "🟨":
            yellows.setdefault(l, set()).add(i)
            local_present.add(l)

    for i, l in local_greens.items():
        greens[i] = l

    for i, sym in enumerate(hint):
        l = word[i]
        if sym == "🟥" and l not in local_present:
            grays.add(l)

def valid(word):
    for i, l in greens.items():
        if word[i] != l:
            return False

    for l, bad_pos in yellows.items():
        if l not in word:
            return False
        if any(word[i] == l for i in bad_pos):
            return False

    if any(l in word for l in grays):
        return False

    return True

def best_guess(words):
    if not words:
        return None
    return max(words, key=lambda w: len(set(w)))

# ---------------- COMMANDS ----------------
@client.on(events.NewMessage(pattern='/host'))
async def host_command(event):
    """Host command to show status and lock to current chat"""
    global CHAT_ID
    CHAT_ID = event.chat_id
    await event.reply(
        f"🤖 **WordSeek Bot Active**\n"
        f"🔒 **Locked to chat**: `{CHAT_ID}`\n"
        f"🎯 **Start word**: `{Config.START_WORD}`\n"
        f"⏱️ **Delay**: `{Config.GUESS_DELAY}s`\n"
        f"🔄 **Auto loop**: `{Config.AUTO_LOOP}`\n\n"
        f"**Ready! Send `/new@WordSeekBot` to start.**",
        parse_mode='md'
    )
    print(f"[HOST] Locked to chat {CHAT_ID}")

@client.on(events.NewMessage(outgoing=True))
async def outgoing_handler(event):
    global CHAT_ID
    text = event.raw_text.lower().strip()
    if text.startswith("/new") and CHAT_ID is None:
        CHAT_ID = event.chat_id
        print(f"[LOCKED] chat = {CHAT_ID}")

# ---------------- GAME HANDLER ----------------
@client.on(events.NewMessage(incoming=True))
async def game_listener(event):
    global game_active, last_guess, possible

    if CHAT_ID is None or event.chat_id != CHAT_ID:
        return

    sender = await event.get_sender()
    if not sender or not sender.bot:
        return

    raw = event.raw_text
    text = raw.lower()
    print(f"[BOT] {raw}")

    # Game start
    if "game started" in text:
        game_active = True
        used_words.clear()
        greens.clear()
        yellows.clear()
        grays.clear()

        with open(Config.WORDLIST_FILE, "r", encoding="utf-8") as f:
            possible = [w for w in json.load(f) if len(w) == 5]

        await asyncio.sleep(Config.GUESS_DELAY)
        await client.send_message(CHAT_ID, Config.START_WORD)
        last_guess = Config.START_WORD
        used_words.add(last_guess)
        print(f"[START] {Config.START_WORD}")
        return

    # Win / End detection
    if (
        "congrats" in text
        or "guessed it correctly" in text
        or "start with /new" in text
    ):
        print("[WIN] detected → auto new")
        game_active = False
        last_guess = None
        possible.clear()

        if Config.AUTO_LOOP:
            await asyncio.sleep(2)
            await client.send_message(CHAT_ID, "/new@WordSeekBot")
            print("[AUTO] /new sent")
        return

    # Hint handling
    if game_active and any(e in text for e in ["🟩", "🟨", "🟥"]):
        emojis = re.findall("[🟩🟨🟥]", text)
        if len(emojis) < 5 or not last_guess:
            return

        hint = "".join(emojis[-5:])
        update_constraints(last_guess, hint)

        if hint == "🟩🟩🟩🟩🟩":
            print("[WIN] emoji solved")
            game_active = False
            last_guess = None
            possible.clear()
            if Config.AUTO_LOOP:
                await asyncio.sleep(2)
                await client.send_message(CHAT_ID, "/new@WordSeekBot")
                print("[AUTO] /new sent")
            return

        possible = [w for w in possible if valid(w) and w not in used_words]
        guess = best_guess(possible)

        if not guess:
            print("[STOP] no possible words")
            game_active = False
            return

        used_words.add(guess)
        last_guess = guess

        await asyncio.sleep(Config.GUESS_DELAY)
        await client.send_message(CHAT_ID, guess)
        print(f"[GUESS] {guess}")

# ---------------- MAIN ----------------
async def main():
    await client.start()
    print("🤖 WordSeek Bot running...")
    print("💡 Send /host in target chat to activate")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
