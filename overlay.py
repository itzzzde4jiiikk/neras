import os
import math
import cairo
from pathlib import Path
from datetime import datetime

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gtk, Gdk, GdkPixbuf, Pango, GLib, GtkLayerShell

import pango_parser
from theme import ThemeManager

class ChatOverlay(Gtk.Window):
    def __init__(self, config):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.config = config
        self.theme_mgr = ThemeManager()
        self.css_provider = Gtk.CssProvider()
        
        self.is_visible_state = False
        self.autohide_timer_id = None
        self.cached_avatars = {}
        self.messages_count = 0
        
        self.setup_window()
        self.setup_css()
        self.setup_ui()
        
        # Periodic check for theme reload from dots-hyprland
        GLib.timeout_add_seconds(2, self.check_theme_reload)

    def setup_window(self):
        self.set_title("Nera Discord Stream Chat Overlay")
        self.set_name("NeraChatOverlay")
        self.get_style_context().add_class("overlay-window")
        
        # Translucent RGBA visual
        screen = Gdk.Screen.get_default()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)
        self.set_app_paintable(True)
        self.connect("draw", self._on_draw)
        
        # Init GtkLayerShell
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        # Using custom namespace so Hyprland does not apply global gtk-layer-shell blur/dim rules
        GtkLayerShell.set_namespace(self, "neras-chat")
        GtkLayerShell.set_keyboard_interactivity(self, False)
        
        # Anchors & Margins
        pos = self.config.get("position", "bottom-right").lower()
        margin_x = int(self.config.get("margin_x", 20))
        margin_y = int(self.config.get("margin_y", 45))
        
        is_right = "right" in pos
        is_bottom = "bottom" in pos
        
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT if is_right else GtkLayerShell.Edge.LEFT, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.BOTTOM if is_bottom else GtkLayerShell.Edge.TOP, True)
        
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.RIGHT if is_right else GtkLayerShell.Edge.LEFT, margin_x)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.BOTTOM if is_bottom else GtkLayerShell.Edge.TOP, margin_y)
        
        # Fixed width, natural auto-height
        width = int(self.config.get("width", 360))
        self.set_default_size(width, -1)
        self.set_size_request(width, -1)
        
        # Click-through region handlers
        self.connect("size-allocate", self._apply_click_through)
        self.connect("map", self._apply_click_through)
        self.connect("realize", self._apply_click_through)

    def _on_draw(self, widget, cr):
        # Guarantee 100% transparent clear background for the window
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)
        return False

    def _apply_click_through(self, *args):
        if self.config.get("click_through", True):
            # Pass all mouse events completely through to windows underneath
            empty_region = cairo.Region()
            self.input_shape_combine_region(empty_region)

    def setup_css(self):
        screen = Gdk.Screen.get_default()
        Gtk.StyleContext.add_provider_for_screen(
            screen,
            self.css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        self.apply_theme()

    def apply_theme(self):
        card_opacity = float(self.config.get("background_opacity", 0.45))
        css_data = self.theme_mgr.generate_css(card_opacity=card_opacity)
        try:
            self.css_provider.load_from_data(css_data.encode("utf-8"))
        except Exception as e:
            print(f"[Overlay] CSS Load Error: {e}")

    def check_theme_reload(self, force=False):
        changed = self.theme_mgr.load_colors()
        if changed or force:
            print("[Overlay] Theme updated! Reloading styles...")
            self.apply_theme()
            self.queue_draw()
        return True

    def setup_ui(self):
        # Direct vertical box - no ScrolledWindow so height is natural and nothing is clipped
        self.msg_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.msg_box.get_style_context().add_class("chat-box")
        self.add(self.msg_box)

    def create_circular_avatar(self, pixbuf, size=24):
        scaled = pixbuf.scale_simple(size, size, GdkPixbuf.InterpType.BILINEAR)
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
        ctx = cairo.Context(surface)
        ctx.arc(size / 2.0, size / 2.0, size / 2.0, 0, 2 * math.pi)
        ctx.clip()
        Gdk.cairo_set_source_pixbuf(ctx, scaled, 0, 0)
        ctx.paint()
        return Gdk.pixbuf_get_from_surface(surface, 0, 0, size, size)

    def get_avatar_image(self, avatar_path, username, size=26):
        cache_dir = Path.home() / ".cache/neras-chat/avatars"
        safe_username = "".join(c for c in (username or "") if c.isalnum() or c in "_-").lower()
        if not avatar_path:
            fallback = cache_dir / f"{safe_username}.png"
            if fallback.exists():
                avatar_path = str(fallback)

        cache_key = (str(avatar_path), username, size)
        if cache_key in self.cached_avatars:
            return Gtk.Image.new_from_pixbuf(self.cached_avatars[cache_key])
            
        if avatar_path and os.path.exists(avatar_path):
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(avatar_path)
                circ = self.create_circular_avatar(pixbuf, size)
                self.cached_avatars[cache_key] = circ
                return Gtk.Image.new_from_pixbuf(circ)
            except Exception as e:
                print(f"[Overlay] Error loading avatar image: {e}")
        
        # Fallback generated circular icon with first letter
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
        ctx = cairo.Context(surface)
        primary_hex = self.theme_mgr.colors.get("primary", "#ffb2b6")
        r, g, b = [int(primary_hex.lstrip("#")[i:i+2], 16)/255.0 for i in (0, 2, 4)]
        
        ctx.arc(size / 2.0, size / 2.0, size / 2.0, 0, 2 * math.pi)
        ctx.set_source_rgba(r, g, b, 0.90)
        ctx.fill()
        
        # Draw initial letter
        letter = (username[:1] if username else "N").upper()
        ctx.select_font_face("Google Sans Flex", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(size * 0.55)
        ctx.set_source_rgb(0.1, 0.1, 0.1)
        ext = ctx.text_extents(letter)
        ctx.move_to(size/2.0 - ext.width/2.0 - ext.x_bearing, size/2.0 - ext.height/2.0 - ext.y_bearing)
        ctx.show_text(letter)
        
        pixbuf = Gdk.pixbuf_get_from_surface(surface, 0, 0, size, size)
        self.cached_avatars[cache_key] = pixbuf
        return Gtk.Image.new_from_pixbuf(pixbuf)

    def add_message(self, msg_data):
        # Compact Discord-like row: [Avatar] [Body: Author+Time / Text]
        card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        card.get_style_context().add_class("message-card")
        
        # Compact circular avatar (26px) aligned to top
        avatar_img = self.get_avatar_image(
            msg_data.get("avatar_path"),
            msg_data.get("author", "User"),
            size=26
        )
        avatar_img.set_valign(Gtk.Align.START)
        card.pack_start(avatar_img, False, False, 0)
        
        # Right body column
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        
        # Meta Row: Author + Badge + Time
        meta_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        
        author_lbl = Gtk.Label()
        author_lbl.set_markup(f"<b>{html_escape(msg_data.get('author', 'Nera'))}</b>")
        author_lbl.get_style_context().add_class("author-label")
        author_lbl.set_xalign(0.0)
        meta_row.pack_start(author_lbl, False, False, 0)
        
        badge = msg_data.get("badge")
        if badge:
            badge_lbl = Gtk.Label(label=badge)
            badge_lbl.get_style_context().add_class("badge-pill")
            meta_row.pack_start(badge_lbl, False, False, 0)
            
        time_str = msg_data.get("timestamp") or datetime.now().strftime("%H:%M")
        time_lbl = Gtk.Label(label=time_str)
        time_lbl.get_style_context().add_class("time-label")
        time_lbl.set_xalign(0.0)
        meta_row.pack_start(time_lbl, False, False, 0)
        
        body.pack_start(meta_row, False, False, 0)
        
        # Content Row
        content_text = msg_data.get("content", "").strip()
        if content_text:
            if len(content_text) > 300:
                content_text = content_text[:297] + "..."
            primary_col = self.theme_mgr.colors.get("primary", "#ffb2b6")
            pango_text = pango_parser.discord_to_pango(content_text, primary_col)
            content_lbl = Gtk.Label()
            content_lbl.set_markup(pango_text)
            content_lbl.set_line_wrap(True)
            content_lbl.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
            
            # Constrain text column wrapping width based on overlay width
            width = int(self.config.get("width", 360))
            content_lbl.set_max_width_chars(max(20, int((width - 50) / 8.5)))
            content_lbl.set_xalign(0.0)
            content_lbl.get_style_context().add_class("content-label")
            body.pack_start(content_lbl, False, False, 0)
            
        # Attachments
        attachments = msg_data.get("attachments", [])
        if attachments:
            for att in attachments:
                att_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
                att_box.get_style_context().add_class("attachment-card")
                att_lbl = Gtk.Label(label=f"📎 {att}")
                att_lbl.get_style_context().add_class("attachment-text")
                att_lbl.set_xalign(0.0)
                att_box.pack_start(att_lbl, False, False, 0)
                body.pack_start(att_box, False, False, 0)

        card.pack_start(body, True, True, 0)
        
        # Enforce maximum 4 messages (FIFO: remove and destroy oldest when reached limit)
        max_msgs = int(self.config.get("max_messages", 4))
        children = self.msg_box.get_children()
        while len(children) >= max_msgs:
            oldest = children.pop(0)
            self.msg_box.remove(oldest)
            oldest.destroy()
            
        self.msg_box.pack_start(card, False, False, 0)
        card.show_all()
        self.msg_box.show_all()
        self.messages_count += 1
        
        # In GtkLayerShell, re-allocate natural size when messages change
        width = int(self.config.get("width", 360))
        self.resize(width, 1)
        self.queue_resize()

        # Re-apply click-through
        self._apply_click_through()
        
        # Auto-hide timer if configured
        auto_hide_sec = int(self.config.get("auto_hide_seconds", 0))
        if auto_hide_sec > 0:
            self.show_autohide(auto_hide_sec)

    def clear_messages(self):
        for child in self.msg_box.get_children():
            self.msg_box.remove(child)
            child.destroy()
        self.messages_count = 0
        width = int(self.config.get("width", 360))
        self.resize(width, 1)
        self.queue_resize()
        self._apply_click_through()
        print("[Overlay] History cleared")

    def toggle_visibility(self):
        if self.is_visible_state:
            self.hide_overlay()
        else:
            self.show_overlay()

    def show_overlay(self):
        self.cancel_autohide()
        self.show_all()
        self._apply_click_through()
        self.is_visible_state = True
        print("[Overlay] Shown")

    def hide_overlay(self):
        self.cancel_autohide()
        self.hide()
        self.is_visible_state = False
        print("[Overlay] Hidden")

    def show_autohide(self, seconds=10):
        if not self.is_visible_state:
            self.show_all()
            self._apply_click_through()
            self.is_visible_state = True
        self.cancel_autohide()
        self.autohide_timer_id = GLib.timeout_add_seconds(seconds, self._on_autohide_timer)

    def _on_autohide_timer(self):
        self.hide_overlay()
        self.autohide_timer_id = None
        return False

    def cancel_autohide(self):
        if self.autohide_timer_id is not None:
            GLib.source_remove(self.autohide_timer_id)
            self.autohide_timer_id = None

def html_escape(s):
    import html
    return html.escape(str(s))
