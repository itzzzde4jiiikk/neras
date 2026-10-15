import os
import sys
import json
import socket
import threading
from pathlib import Path
from gi.repository import GLib

def get_socket_path():
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
    if runtime_dir and os.path.isdir(runtime_dir):
        return Path(runtime_dir) / "neras_chat.sock"
    return Path("/tmp/neras_chat.sock")

class IPCServer:
    def __init__(self, overlay):
        self.overlay = overlay
        self.sock_path = get_socket_path()
        self.running = False

    def start(self):
        self.running = True
        if self.sock_path.exists():
            try:
                self.sock_path.unlink()
            except Exception:
                pass
        
        t = threading.Thread(target=self._listen_loop, daemon=True)
        t.start()

    def _listen_loop(self):
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(self.sock_path))
        server.listen(5)
        print(f"[IPC] Listening on {self.sock_path}")
        
        while self.running:
            try:
                conn, _ = server.accept()
                with conn:
                    data = conn.recv(4096)
                    if data:
                        try:
                            req = json.loads(data.decode("utf-8"))
                            resp = self._handle_request(req)
                            conn.sendall(json.dumps(resp).encode("utf-8"))
                        except Exception as e:
                            conn.sendall(json.dumps({"error": str(e)}).encode("utf-8"))
            except Exception as e:
                if self.running:
                    print(f"[IPC] Error accepting connection: {e}")

    def _handle_request(self, req):
        action = req.get("action")
        if action == "toggle":
            GLib.idle_add(self.overlay.toggle_visibility)
            return {"status": "ok", "action": "toggle"}
        elif action == "show":
            GLib.idle_add(self.overlay.show_overlay)
            return {"status": "ok", "action": "show"}
        elif action == "hide":
            GLib.idle_add(self.overlay.hide_overlay)
            return {"status": "ok", "action": "hide"}
        elif action == "clear":
            GLib.idle_add(self.overlay.clear_messages)
            return {"status": "ok", "action": "clear"}
        elif action == "reload_theme":
            GLib.idle_add(self.overlay.check_theme_reload, True)
            return {"status": "ok", "action": "reload_theme"}
        elif action == "test":
            text = req.get("text", "Привет! Это тестовое сообщение.")
            author = req.get("author", self.overlay.config.get("target_username", "nera").capitalize())
            safe_author = "".join(c for c in author if c.isalnum() or c in "_-").lower()
            cache_dir = Path.home() / ".cache/neras-chat/avatars"
            avatar_path = req.get("avatar_path")
            if not avatar_path and (cache_dir / f"{safe_author}.png").exists():
                avatar_path = str(cache_dir / f"{safe_author}.png")
            msg_payload = {
                "author": author,
                "avatar_path": avatar_path,
                "content": text,
                "timestamp": None,
                "badge": "DM",
                "attachments": req.get("attachments", [])
            }
            GLib.idle_add(self.overlay.add_message, msg_payload)
            return {"status": "ok", "action": "test"}
        elif action == "status":
            return {
                "status": "ok",
                "visible": self.overlay.is_visible_state,
                "messages": len(self.overlay.msg_box.get_children())
            }
        return {"error": "unknown_action"}

def send_command(action, **kwargs):
    sock_path = get_socket_path()
    if not sock_path.exists():
        return False, "Daemon is not running"
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(2.0)
            client.connect(str(sock_path))
            payload = {"action": action}
            payload.update(kwargs)
            client.sendall(json.dumps(payload).encode("utf-8"))
            data = client.recv(4096)
            if data:
                return True, json.loads(data.decode("utf-8"))
            return True, {}
    except Exception as e:
        return False, str(e)

if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "toggle"
    extra_arg = sys.argv[2] if len(sys.argv) > 2 else None
    
    if action == "test":
        success, resp = send_command("test", text=extra_arg or "Привет! Как там игра? ✨")
    elif action in ["toggle", "show", "hide", "clear", "reload_theme", "status"]:
        success, resp = send_command(action)
    else:
        print(f"Usage: {sys.argv[0]} [toggle|show|hide|clear|reload_theme|test|status] [test_message]")
        sys.exit(1)
        
    if not success:
        print(f"Error: {resp}")
        sys.exit(1)
    else:
        print(f"Success: {resp}")
