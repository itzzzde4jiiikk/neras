import json
import os
from pathlib import Path

DEFAULT_COLORS = {
    "background": "#1a1112",
    "surface": "#1a1112",
    "surface_container": "#271d1e",
    "surface_container_high": "#322828",
    "surface_container_highest": "#3d3232",
    "on_surface": "#f0dede",
    "on_surface_variant": "#d7c1c2",
    "primary": "#ffb2b6",
    "on_primary": "#561d23",
    "primary_container": "#723338",
    "on_primary_container": "#ffdada",
    "secondary": "#e6bdbe",
    "tertiary": "#e7c08e",
    "outline": "#9f8c8c",
    "outline_variant": "#524343"
}

def hex_to_rgb(hex_code: str):
    hex_code = hex_code.lstrip("#")
    if len(hex_code) == 3:
        hex_code = "".join([c*2 for c in hex_code])
    if len(hex_code) >= 6:
        return int(hex_code[0:2], 16), int(hex_code[2:4], 16), int(hex_code[4:6], 16)
    return 0, 0, 0

def hex_to_rgba(hex_code: str, alpha: float):
    r, g, b = hex_to_rgb(hex_code)
    return f"rgba({r}, {g}, {b}, {alpha:.2f})"

class ThemeManager:
    def __init__(self):
        self.colors_file = Path.home() / ".local/state/quickshell/user/generated/colors.json"
        self.last_mtime = 0
        self.colors = DEFAULT_COLORS.copy()
        self.load_colors()

    def load_colors(self) -> bool:
        if self.colors_file.exists():
            try:
                mtime = os.path.getmtime(self.colors_file)
                if mtime != self.last_mtime:
                    self.last_mtime = mtime
                    with open(self.colors_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        self.colors.update(data)
                    return True
            except Exception as e:
                print(f"[Theme] Error reading colors.json: {e}")
        return False

    def generate_css(self, card_opacity: float = 0.45) -> str:
        c = self.colors
        border_col = hex_to_rgba(c.get("outline_variant", "#524343"), 0.5)
        primary = c.get("primary", "#ffb2b6")
        on_surface_muted = c.get("on_surface_variant", "#d7c1c2")
        badge_border = hex_to_rgba(primary, 0.4)
        
        # Subtle translucent card background and border derived from Matugen palette
        card_bg = hex_to_rgba(c.get("surface_container_lowest", "#140c0c"), card_opacity)
        card_border = hex_to_rgba(c.get("outline_variant", "#524343"), 0.22)

        css = f"""
        * {{
            font-family: 'Google Sans Flex', 'Rubik', 'Noto Sans', 'Noto Color Emoji', 'Twemoji', sans-serif;
        }}

        window, window.background, window.overlay-window, .overlay-window {{
            background: transparent;
            background-color: transparent;
            border: none;
            box-shadow: none;
        }}

        .chat-box {{
            background: transparent;
            background-color: transparent;
            padding: 0;
            margin: 0;
        }}

        .message-card {{
            background-color: {card_bg};
            border: 1px solid {card_border};
            border-radius: 12px;
            padding: 6px 10px;
            margin-bottom: 5px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
        }}

        .author-label {{
            color: {primary};
            font-weight: 700;
            font-size: 13px;
            text-shadow: 0 1px 2px rgba(0, 0, 0, 0.9);
        }}

        .time-label {{
            color: {on_surface_muted};
            font-size: 10.5px;
            font-weight: 500;
            margin-left: 6px;
            text-shadow: 0 1px 2px rgba(0, 0, 0, 0.9);
        }}

        .badge-pill {{
            background-color: rgba(0, 0, 0, 0.45);
            border: 1px solid {badge_border};
            color: {primary};
            font-size: 9.5px;
            font-weight: 600;
            border-radius: 4px;
            padding: 0px 4px;
            margin-left: 4px;
            text-shadow: 0 1px 2px rgba(0, 0, 0, 0.9);
        }}

        .content-label {{
            color: #ffffff;
            font-size: 13px;
            font-weight: 500;
            text-shadow: 0 1px 2px rgba(0, 0, 0, 0.95), 0 0 2px rgba(0, 0, 0, 0.95);
        }}

        .attachment-card {{
            background-color: rgba(0, 0, 0, 0.45);
            border: 1px solid {border_col};
            border-radius: 6px;
            padding: 2px 6px;
            margin-top: 3px;
        }}

        .attachment-text {{
            color: {primary};
            font-size: 11px;
            font-weight: 500;
            text-shadow: 0 1px 2px rgba(0, 0, 0, 0.9);
        }}
        """
        return css
