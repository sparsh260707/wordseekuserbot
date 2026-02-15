# =========================
# IMPORTS
# =========================
import os
import sys
import time
import random
import asyncio
import re
import json
import requests

from telethon import TelegramClient, events
from config import Config


# =========================
# CONFIG VALUES (from config.py)
# =========================
START_WORD = Config.START_WORD
WORDLIST_FILE = Config.WORDLIST_FILE
GUESS_DELAY = Config.GUESS_DELAY
AUTO_LOOP = Config.AUTO_LOOP

# Remove the old hardcoded config section
def init_client(api_id, api_hash, session_name="userbot_solver"):
    """Initialize client - MUST be called before use"""
    global client, _client
    client = TelegramClient(session_name, api_id, api_hash)
    _client = client
    return client

# ---------------- STATE ----------------
possible = []
used_words = set()
last_guess = None

greens = {}
yellows = {}
grays = set()

game_active = False
CHAT_ID = None
HOSTS = set()

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

# ---------------- OUTGOING (LOCK) ----------------
async def outgoing_handler(event):
    """Outgoing handler - requires client to be initialized"""
    global CHAT_ID
    if 'client' not in globals():
        return
        
    text = event.raw_text.lower().strip()
    if text.startswith("/new") and CHAT_ID is None:
        CHAT_ID = event.chat_id
        print(f"[LOCKED] chat = {CHAT_ID}")

# ---------------- INCOMING ----------------
async def game_listener(event):
    """Game listener - requires client to be initialized"""
    global game_active, last_guess, possible
    
    if 'client' not in globals() or CHAT_ID is None or event.chat_id != CHAT_ID or not HOSTS:
        return

    sender = await event.get_sender()
    if not sender or not sender.bot:
        return

    raw = event.raw_text
    text = raw.lower()
    print(f"[BOT] {raw}")

    # 🟢 GAME START
    if "game started" in text:
        game_active = True
        used_words.clear()
        greens.clear()
        yellows.clear()
        grays.clear()

        with open(WORDLIST_FILE, "r", encoding="utf-8") as f:
            possible = [w for w in json.load(f) if len(w) == 5]

        await asyncio.sleep(GUESS_DELAY)
        await client.send_message(CHAT_ID, START_WORD)

        last_guess = START_WORD
        used_words.add(last_guess)
        print(f"[START] {START_WORD}")
        return

    # 🟢 WIN / END DETECTION (REAL FIX)
    if (
        "congrats" in text
        or "guessed it correctly" in text
        or "start with /new" in text
    ):
        print("[WIN] detected → auto new")

        game_active = False
        last_guess = None
        possible.clear()

        if AUTO_LOOP:
            await asyncio.sleep(2)
            await client.send_message(CHAT_ID, "/new@WordSeekBot")
            print("[AUTO] /new sent")

        return

    # 🟡 HINT HANDLING
    if game_active and any(e in text for e in ["🟩", "🟨", "🟥"]):
        emojis = re.findall("[🟩🟨🟥]", text)
        if len(emojis) < 5 or not last_guess:
            return

        hint = "".join(emojis[-5:])
        update_constraints(last_guess, hint)

        # 🟩🟩🟩🟩🟩 fallback win
        if hint == "🟩🟩🟩🟩🟩":
            print("[WIN] emoji solved")

            game_active = False
            last_guess = None
            possible.clear()

            if AUTO_LOOP:
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

        await asyncio.sleep(GUESS_DELAY)
        await client.send_message(CHAT_ID, guess)
        print(f"[GUESS] {guess}")

# ---------------- CONTROL API ----------------
async def start_solver(api_id, api_hash):
    """Initialize and start solver"""
    global client, HOSTS
    HOSTS.add(1)  # Enable hosting
    init_client(api_id, api_hash)
    await client.start()
    
    # Register event handlers AFTER client creation
    client.add_event_handler(outgoing_handler, events.NewMessage(outgoing=True))
    client.add_event_handler(game_listener, events.NewMessage(incoming=True))
    
    print("✅ Solver initialized and running!")

async def stop_solver():
    """Stop solver"""
    global HOSTS, client
    HOSTS.clear()
    if client and client.is_connected():
        await client.disconnect()

async def main():
    """Original standalone main"""
    global client, HOSTS
    HOSTS.add(1)  # Enable for standalone
    init_client(33508729, "b5b3408af6901b84eb3fe8b3cf2d49c5")
    await client.start()
    
    client.add_event_handler(outgoing_handler, events.NewMessage(outgoing=True))
    client.add_event_handler(game_listener, events.NewMessage(incoming=True))
    
    print("Userbot running (FINAL AUTO-NEW)")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
