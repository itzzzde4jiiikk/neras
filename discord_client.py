import os
import sys
import json
import time
import asyncio
import aiohttp
import websockets
from pathlib import Path
from datetime import datetime
from gi.repository import GLib

CACHE_DIR = Path.home() / ".cache/neras-chat/avatars"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

class DiscordGatewayClient:
    def __init__(self, config, on_message_cb):
        self.config = config
        self.on_message_cb = on_message_cb
        
        self.raw_token = (self.config.get("discord_token") or "").strip()
        self.target_user_id = str(self.config.get("target_user_id") or "").strip()
        self.target_username = str(self.config.get("target_username") or "").strip().lower()
        self.channel_id = str(self.config.get("channel_id") or "").strip()
        
        # Token type detection:
        # If explicitly marked as bot or token starts with "Bot ", treat as bot. Otherwise default to user token.
        if self.raw_token.startswith("Bot "):
            self.is_bot = True
            self.auth_token = self.raw_token.replace("Bot ", "").strip()
            self.auth_header = self.raw_token
        elif self.config.get("is_bot", False):
            self.is_bot = True
            self.auth_token = self.raw_token
            self.auth_header = f"Bot {self.raw_token}"
        else:
            self.is_bot = False
            self.auth_token = self.raw_token
            self.auth_header = self.raw_token
            
        self.guilds_map = {}
        self.ws = None
        self.session = None
        self.heartbeat_task = None
        self.running = False
        self.last_seq = None

    def start_in_background(self):
        if not self.raw_token:
            print("[Discord] No discord_token configured in config.json. Gateway client skipped.")
            return
        self.running = True
        loop = asyncio.new_event_loop()
        import threading
        t = threading.Thread(target=self._run_loop, args=(loop,), daemon=True)
        t.start()

    def _run_loop(self, loop):
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._main_task())

    async def _main_task(self):
        connector = aiohttp.TCPConnector(ssl=True)
        self.session = aiohttp.ClientSession(connector=connector)
        
        # Fetch initial history if channel_id is provided
        if self.channel_id:
            await self._fetch_history()

        while self.running:
            try:
                await self._connect_gateway()
            except Exception as e:
                print(f"[Discord] Connection error: {e}. Reconnecting in 5s...")
                await asyncio.sleep(5)

    async def _download_avatar(self, user_id, avatar_hash):
        if not avatar_hash:
            return None
        cached_file = CACHE_DIR / f"{avatar_hash}.png"
        if cached_file.exists():
            return str(cached_file)
        
        url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.png?size=64"
        try:
            async with self.session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    with open(cached_file, "wb") as f:
                        f.write(data)
                    return str(cached_file)
        except Exception as e:
            print(f"[Discord] Avatar download error: {e}")
        return None

    async def _fetch_history(self):
        url = f"https://discord.com/api/v10/channels/{self.channel_id}/messages?limit=10"
        headers = {"Authorization": self.auth_header}
        try:
            async with self.session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    messages = await resp.json()
                    # Chronological order
                    messages.reverse()
                    print(f"[Discord] Fetched {len(messages)} recent messages from channel {self.channel_id}")
                    for msg in messages:
                        if self._is_target_author(msg):
                            await self._handle_message(msg)
                else:
                    text = await resp.text()
                    print(f"[Discord] Error fetching history: {resp.status} - {text}")
        except Exception as e:
            print(f"[Discord] Error fetching history: {e}")

    def _is_target_author(self, msg):
        author = msg.get("author", {})
        uid = str(author.get("id", ""))
        uname = (author.get("username") or "").lower()
        gname = (author.get("global_name") or "").lower()
        nick = (msg.get("member", {}).get("nick") or "").lower()
        
        if self.target_user_id and uid == self.target_user_id:
            return True
        if self.target_username:
            target = self.target_username
            if target == uname or target == gname or target == nick:
                return True
            if target in uname or target in gname or target in nick:
                return True
        if not self.target_user_id and not self.target_username:
            return True
        return False

    async def _handle_message(self, msg):
        author = msg.get("author", {})
        display_name = (
            msg.get("member", {}).get("nick") 
            or author.get("global_name") 
            or author.get("username") 
            or "User"
        )
        content = msg.get("content", "")
        uid = author.get("id")
        avatar_hash = author.get("avatar")
        avatar_path = await self._download_avatar(uid, avatar_hash)
        
        # Format timestamp
        ts_raw = msg.get("timestamp")
        time_str = datetime.now().strftime("%H:%M")
        if ts_raw:
            try:
                dt = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                time_str = dt.astimezone().strftime("%H:%M")
            except Exception:
                pass
                
        # Badge: Guild Name or DM
        guild_id = msg.get("guild_id")
        if guild_id:
            badge = self.guilds_map.get(str(guild_id), "Сервер")
        else:
            badge = "DM"

        # Attachments
        attachments = [a.get("filename", "file") for a in msg.get("attachments", [])]
        
        msg_payload = {
            "id": msg.get("id"),
            "author": display_name,
            "username": author.get("username"),
            "user_id": uid,
            "avatar_path": avatar_path,
            "content": content,
            "timestamp": time_str,
            "badge": badge,
            "attachments": attachments
        }
        
        print(f"[Discord Gateway] Matched message from {display_name} in {badge}: {content}")
        GLib.idle_add(self.on_message_cb, msg_payload)

    async def _connect_gateway(self):
        gateway_url = "wss://gateway.discord.gg/?v=10&encoding=json"
        print(f"[Discord] Connecting to Discord Gateway (mode: {'Bot' if self.is_bot else 'User'})...")
        async with websockets.connect(gateway_url, max_size=10*1024*1024) as ws:
            self.ws = ws
            async for raw_msg in ws:
                data = json.loads(raw_msg)
                op = data.get("op")
                seq = data.get("s")
                if seq is not None:
                    self.last_seq = seq
                t = data.get("t")
                d = data.get("d")

                if op == 10:  # HELLO
                    heartbeat_interval = d["heartbeat_interval"] / 1000.0
                    if self.heartbeat_task:
                        self.heartbeat_task.cancel()
                    self.heartbeat_task = asyncio.create_task(self._heartbeat(heartbeat_interval))
                    await self._identify()

                elif op == 11:  # HEARTBEAT ACK
                    pass

                elif op == 0:  # DISPATCH
                    if t == "READY":
                        # Cache guild names
                        for g in d.get("guilds", []):
                            gid = str(g.get("id", ""))
                            gname = g.get("name")
                            if gid and gname:
                                self.guilds_map[gid] = gname
                        uname = d.get('user', {}).get('username')
                        print(f"[Discord] Connected & Identified as @{uname}! Cached {len(self.guilds_map)} servers.")
                    elif t == "GUILD_CREATE":
                        gid = str(d.get("id", ""))
                        gname = d.get("name")
                        if gid and gname:
                            self.guilds_map[gid] = gname
                    elif t == "MESSAGE_CREATE":
                        if self._is_target_author(d):
                            await self._handle_message(d)

    async def _heartbeat(self, interval):
        try:
            while True:
                await asyncio.sleep(interval)
                if self.ws:
                    await self.ws.send(json.dumps({"op": 1, "d": self.last_seq}))
        except asyncio.CancelledError:
            pass

    async def _identify(self):
        if self.is_bot:
            payload = {
                "op": 2,
                "d": {
                    "token": f"Bot {self.auth_token}",
                    "intents": 33280,  # GUILDS | GUILD_MESSAGES | DIRECT_MESSAGES | MESSAGE_CONTENT
                    "properties": {
                        "os": "linux",
                        "browser": "nera_chat",
                        "device": "nera_chat"
                    }
                }
            }
        else:
            payload = {
                "op": 2,
                "d": {
                    "token": self.auth_token,
                    "capabilities": 16381,
                    "properties": {
                        "os": "Linux",
                        "browser": "Discord Client",
                        "release_channel": "stable",
                        "client_version": "1.0.9006",
                        "os_version": "6.6",
                        "os_arch": "x64"
                    }
                }
            }
        await self.ws.send(json.dumps(payload))
