import html
import re

EMOJI_SHORTCODES = {
    # Custom / Russian internet favorites
    ":hihi:": "🤭",
    ":kek:": "😆",
    ":kekw:": "🤣",
    ":nya:": "🐱",
    ":pepe:": "🐸",
    ":monkas:": "😰",
    ":pog:": "😲",
    ":poggers:": "😲",
    ":ayaya:": "✨",
    ":uwu:": "🥺",
    ":owo:": "😻",
    # Faces & Expressions
    ":smile:": "😄",
    ":slight_smile:": "🙂",
    ":grin:": "😁",
    ":joy:": "😂",
    ":rofl:": "🤣",
    ":sweat_smile:": "😅",
    ":laughing:": "😆",
    ":wink:": "😉",
    ":blush:": "😊",
    ":innocent:": "😇",
    ":heart_eyes:": "😍",
    ":kissing_heart:": "😘",
    ":kissing:": "😗",
    ":relaxed:": "☺️",
    ":yum:": "😋",
    ":stuck_out_tongue:": "😛",
    ":stuck_out_tongue_winking_eye:": "😜",
    ":sunglasses:": "😎",
    ":smirk:": "😏",
    ":unamused:": "😒",
    ":disappointed:": "😞",
    ":pensive:": "😔",
    ":worried:": "😟",
    ":confused:": "😕",
    ":pleading_face:": "🥺",
    ":pleading:": "🥺",
    ":sob:": "😭",
    ":cry:": "😢",
    ":scream:": "😱",
    ":rage:": "😡",
    ":angry:": "😠",
    ":thinking:": "🤔",
    ":shrug:": "🤷",
    ":facepalm:": "🤦",
    ":skull:": "💀",
    ":clown:": "🤡",
    ":ghost:": "👻",
    ":alien:": "👽",
    ":poop:": "💩",
    ":hugs:": "🤗",
    ":grimacing:": "😬",
    ":neutral_face:": "😐",
    ":expressionless:": "😑",
    ":sleeping:": "😴",
    # Hearts & Symbols
    ":heart:": "❤️",
    ":orange_heart:": "🧡",
    ":yellow_heart:": "💛",
    ":green_heart:": "💚",
    ":blue_heart:": "💙",
    ":purple_heart:": "💜",
    ":black_heart:": "🖤",
    ":white_heart:": "🤍",
    ":sparkling_heart:": "💖",
    ":broken_heart:": "💔",
    ":fire:": "🔥",
    ":sparkles:": "✨",
    ":star:": "⭐",
    ":star2:": "🌟",
    ":collision:": "💥",
    ":zap:": "⚡",
    ":100:": "💯",
    ":check:": "✅",
    ":white_check_mark:": "✅",
    ":x:": "❌",
    # Gestures
    ":thumbsup:": "👍",
    ":+1:": "👍",
    ":thumbsdown:": "👎",
    ":-1:": "👎",
    ":clap:": "👏",
    ":pray:": "🙏",
    ":wave:": "👋",
    ":ok_hand:": "👌",
    ":v:": "✌️",
    ":punch:": "👊",
    ":muscle:": "💪",
    ":eyes:": "👀",
    # Animals & Items
    ":cat:": "🐱",
    ":dog:": "🐶",
    ":fox:": "🦊",
    ":bear:": "🐻",
    ":panda:": "🐼",
    ":frog:": "🐸",
    ":rabbit:": "🐰",
    ":tada:": "🎉",
    ":gift:": "🎁",
    ":coffee:": "☕",
    ":tea:": "🍵",
    ":pizza:": "🍕",
    ":cake:": "🎂",
}

TEXT_EMOTICONS = [
    (r'(?<!\S)&lt;3(?!\S)', '❤️'),    # <3
    (r'(?<!\S):3(?!\S)', '🐱'),      # :3
    (r'(?<!\S):-?\)(?!\S)', '😊'),   # :) or :-)
    (r'(?<!\S):-?D(?!\S)', '😃'),   # :D or :-D
    (r'(?<!\S);-?\)(?!\S)', '😉'),   # ;) or ;-)
    (r'(?<!\S):-?[Pp](?!\S)', '😛'), # :P or :p
    (r'(?<!\S):-?\((?!\S)', '🙁'),   # :( or :-(
    (r'(?<!\S):-?[Oo](?!\S)', '😮'), # :O or :o
    (r'(?<!\S)[xX][dD](?!\S)', '😆'), # xD or XD
    (r'(?<!\S)-_-(?!\S)', '😑'),    # -_-
    (r'(?<!\S)\^\_\^(?!\S)', '😊'),  # ^_^
    (r'(?<!\S)\^\^(?!\S)', '😊'),    # ^^
    (r'(?<!\S)T_T(?!\S)', '😭'),    # T_T
    (r'(?<!\S)&gt;_&lt;(?!\S)', '😣'), # >_<
    (r'(?<!\S)&gt;\.&lt;(?!\S)', '😣'), # >.<
]

def discord_to_pango(text: str, accent_color: str = "#ffb2b6") -> str:
    if not text:
        return ""

    # Normalize newlines
    text = text.replace("\r\n", "\n")

    # 1. Escape HTML special characters
    s = html.escape(text)

    # 2. Code blocks ```lang\ncode```
    def replace_codeblock(m):
        code = m.group(1).strip()
        return f'<tt><span font_family="monospace" background="rgba(0,0,0,0.3)">\n{code}\n</span></tt>'
    s = re.sub(r'```(?:[a-zA-Z0-9_+-]*\n)?([\s\S]*?)```', replace_codeblock, s)

    # 3. Inline code `code`
    s = re.sub(r'`([^`\n]+)`', r'<tt><span font_family="monospace" background="rgba(0,0,0,0.25)"> \1 </span></tt>', s)

    # 4. Links (http / https) before emoticons so URLs aren't damaged
    def replace_url(m):
        url = m.group(0)
        return rf'<span foreground="{accent_color}"><u>{url}</u></span>'
    s = re.sub(r'https?://[^\s<>"]+', replace_url, s)

    # 5. Mentions <@id> or <@!id>
    s = re.sub(
        r'&lt;@!?([0-9]+)&gt;',
        rf'<span foreground="{accent_color}"><b>@user</b></span>',
        s
    )

    # 6. Channel mentions <#id>
    s = re.sub(
        r'&lt;#([0-9]+)&gt;',
        rf'<span foreground="{accent_color}">#channel</span>',
        s
    )

    # 7. Discord custom emojis <:name:id> or <a:name:id>
    def replace_custom_emoji(m):
        name = m.group(1)
        shortcode = f":{name}:"
        if shortcode in EMOJI_SHORTCODES:
            return EMOJI_SHORTCODES[shortcode]
        return f'<b>:{name}:</b>'
    s = re.sub(r'&lt;a?:([a-zA-Z0-9_]+):[0-9]+&gt;', replace_custom_emoji, s)

    # 8. Shortcodes like :hihi:, :smile:, :heart:
    s = re.sub(r':([a-zA-Z0-9_+-]+):', lambda m: EMOJI_SHORTCODES.get(m.group(0), m.group(0)), s)

    # 9. Text emoticons
    for pattern, repl in TEXT_EMOTICONS:
        s = re.sub(pattern, repl, s)

    # 10. Markdown: Bold **text**
    s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)

    # 11. Markdown: Underline __text__
    s = re.sub(r'__(.+?)__', r'<u>\1</u>', s)

    # 12. Markdown: Italic *text* or _text_
    s = re.sub(r'\*([^*]+?)\*', r'<i>\1</i>', s)
    s = re.sub(r'\b_([^_]+?)_\b', r'<i>\1</i>', s)

    # 13. Markdown: Strikethrough ~~text~~
    s = re.sub(r'~~(.+?)~~', r'<s>\1</s>', s)

    return s
