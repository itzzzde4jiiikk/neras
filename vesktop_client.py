import os
import json
import base64
import hashlib
import asyncio
import socket
import threading
from pathlib import Path
import websockets
from datetime import datetime
from gi.repository import GLib

AVATAR_CACHE_DIR = Path.home() / ".cache/neras-chat/avatars"
AVATAR_CACHE_DIR.mkdir(parents=True, exist_ok=True)

class VesktopBridge:
    def __init__(self, config, on_message_cb):
        self.config = config
        self.on_message_cb = on_message_cb
        self.target_user_id = str(self.config.get("target_user_id") or "").strip()
        self.target_username = str(self.config.get("target_username") or "").strip().lower()
        self.ws_port = 42070
        self.udp_port = 42069
        self.running = False

    def start_in_background(self):
        self.running = True
        # Thread for WebSocket server
        t_ws = threading.Thread(target=self._run_ws_server, daemon=True)
        t_ws.start()
        # Thread for UDP server
        t_udp = threading.Thread(target=self._run_udp_server, daemon=True)
        t_udp.start()

    def _run_ws_server(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._ws_server())
        except Exception as e:
            print(f"[Vesktop WS] Error starting server on port {self.ws_port}: {e}")

    async def _ws_server(self):
        print(f"[Vesktop Bridge] Listening for Vencord/Vesktop notifications on ws://127.0.0.1:{self.ws_port}...")
        async with websockets.serve(self._handle_ws_client, "127.0.0.1", self.ws_port):
            await asyncio.Future()  # run forever

    async def _handle_ws_client(self, websocket):
        print("[Vesktop Bridge] Vencord client connected!")
        try:
            async for raw in websocket:
                try:
                    data = json.loads(raw)
                    # Vencord XSOverlay sends { "jsonData": "..." } or direct notification object
                    if "jsonData" in data:
                        notif = json.loads(data["jsonData"])
                    else:
                        notif = data
                    self._process_notification(notif)
                except Exception as e:
                    print(f"[Vesktop Bridge] Error parsing message: {e}")
        except websockets.exceptions.ConnectionClosed:
            pass

    def _run_udp_server(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.bind(("127.0.0.1", self.udp_port))
            print(f"[Vesktop Bridge] Listening for UDP notifications on 127.0.0.1:{self.udp_port}...")
            while self.running:
                data, _ = sock.recvfrom(65535)
                try:
                    notif = json.loads(data.decode("utf-8"))
                    self._process_notification(notif)
                except Exception as e:
                    print(f"[Vesktop UDP] Error parsing packet: {e}")
        except Exception as e:
            print(f"[Vesktop UDP] Port {self.udp_port} bind error: {e}")
        finally:
            sock.close()

    def _process_notification(self, notif):
        title = notif.get("title", "")
        content = notif.get("content", "")
        
        # Check target
        title_lower = title.lower()
        if self.target_username and self.target_username not in title_lower:
            # If target username is not in the notification title, ignore
            return
            
        time_str = datetime.now().strftime("%H:%M")
        
        # Clean title (Vencord formats title like "Username (Server, #channel)")
        author = title
        badge = None
        if "(" in title and ")" in title:
            parts = title.split("(", 1)
            author = parts[0].strip()
            badge = parts[1].rstrip(")").strip()

        # Extract and cache avatar from notification
        avatar_path = None
        icon_data = notif.get("icon")
        if icon_data and isinstance(icon_data, str) and icon_data != "default" and len(icon_data) > 30:
            try:
                if "," in icon_data:
                    icon_data = icon_data.split(",", 1)[1]
                raw_bytes = base64.b64decode(icon_data)
                icon_hash = hashlib.md5(raw_bytes).hexdigest()
                cached_file = AVATAR_CACHE_DIR / f"{icon_hash}.png"
                if not cached_file.exists():
                    cached_file.write_bytes(raw_bytes)
                avatar_path = str(cached_file)
                
                # Also save author alias for reuse
                safe_author = "".join(c for c in author if c.isalnum() or c in "_-").lower()
                if safe_author:
                    author_cache = AVATAR_CACHE_DIR / f"{safe_author}.png"
                    author_cache.write_bytes(raw_bytes)
            except Exception as e:
                print(f"[Vesktop Bridge] Error decoding avatar icon: {e}")

        if not avatar_path:
            safe_author = "".join(c for c in author if c.isalnum() or c in "_-").lower()
            author_cache = AVATAR_CACHE_DIR / f"{safe_author}.png"
            if author_cache.exists():
                avatar_path = str(author_cache)

        msg_payload = {
            "id": str(datetime.now().timestamp()),
            "author": author,
            "avatar_path": avatar_path,
            "content": content,
            "timestamp": time_str,
            "badge": badge,
            "attachments": []
        }
        
        GLib.idle_add(self.on_message_cb, msg_payload)
