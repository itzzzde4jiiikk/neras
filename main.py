#!/usr/bin/env python3
import os
import sys
import json
import signal
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gtk, GLib

from overlay import ChatOverlay
from ipc import IPCServer
from discord_client import DiscordGatewayClient
from vesktop_client import VesktopBridge

def load_config():
    cfg_file = BASE_DIR / "config.json"
    if cfg_file.exists():
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[Main] Error loading config.json: {e}")
    return {}

def main():
    pid_file = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp")) / "neras_chat.pid"
    pid_file.write_text(str(os.getpid()))

    config = load_config()
    print("=======================================")
    print(" Nera's Discord Stream Chat Overlay   ")
    print(f" Target User: {config.get('target_username') or config.get('target_user_id') or 'All'}")
    print(f" Position: {config.get('position', 'bottom-right')}")
    print("=======================================")

    # Initialize Overlay Window
    overlay = ChatOverlay(config)
    
    # Initialize IPC Server (for Hyprland keybinds)
    ipc = IPCServer(overlay)
    ipc.start()

    # Callback when a new message arrives from Discord or Vesktop
    def on_message_received(msg_data):
        print(f"[Chat] {msg_data.get('author')}: {msg_data.get('content')}")
        overlay.add_message(msg_data)

    # Start Discord Gateway Client (if token provided)
    if config.get("discord_token"):
        discord_client = DiscordGatewayClient(config, on_message_received)
        discord_client.start_in_background()
    else:
        print("[Main] No discord_token specified. Running with Vesktop bridge and IPC test support.")

    # Start Vesktop / Vencord XSOverlay Bridge (if enabled)
    if config.get("enable_vesktop_bridge", True):
        vesktop_bridge = VesktopBridge(config, on_message_received)
        vesktop_bridge.start_in_background()

    # Initial visibility
    if config.get("default_visible", False):
        overlay.show_overlay()
    else:
        print("[Main] Overlay initialized in hidden state. Use hotkey to show.")

    # Signal handlers for clean exit
    def handle_sigint(signum, frame):
        print("\n[Main] Exiting...")
        Gtk.main_quit()

    signal.signal(signal.SIGINT, handle_sigint)
    signal.signal(signal.SIGTERM, handle_sigint)

    # Run GTK main loop
    try:
        Gtk.main()
    finally:
        if pid_file.exists():
            pid_file.unlink()

if __name__ == "__main__":
    main()
