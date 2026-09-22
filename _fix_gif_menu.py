import ast, re, sys
from pathlib import Path

p = Path.home() / "Desktop" / "vuadaomo" / "vuadaomo.py"
src = p.read_text(encoding="utf-8")
changed = []

# 1. cmd_start: gui animation kem caption+menu, khong tach
new_start = '''async def cmd_start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    cap = main_caption(); kb = kb_main()
    if GIF_URL:
        try:
            await u.message.reply_animation(GIF_URL, caption=cap, parse_mode=ParseMode.HTML, reply_markup=kb)
            return
        except Exception as e:
            print("[start] animation fail: " + str(e))
    try:
        await u.message.reply_text(cap, parse_mode=ParseMode.HTML, reply_markup=kb)
    except: pass'''

m = re.search(r"^async def cmd_start\([^)]*\):\s*$", src, re.MULTILINE)
if m:
    nxt = re.search(r"^(?:async def |def |class )", src[m.end():], re.MULTILINE)
    end = m.end() + nxt.start() if nxt else len(src)
    src = src[:m.start()] + new_start + "\n\n\n" + src[end:]
    changed.append("cmd_start")

# 2. edit_msg: chi edit caption, khong xoa+gui lai
new_edit = '''async def edit_msg(q, txt, kb):
    m = q.message
    try:
        if m.animation or m.photo:
            await q.edit_message_caption(caption=txt, parse_mode=ParseMode.HTML, reply_markup=kb)
            return
        await q.edit_message_text(txt, parse_mode=ParseMode.HTML, reply_markup=kb)
    except Exception as e:
        msg = str(e)
        if "message is not modified" in msg:
            return
        # chi khi Telegram that su tu choi edit - gui animation moi
        try:
            if GIF_URL:
                await q.get_bot().send_animation(q.message.chat_id, GIF_URL,
                    caption=txt, parse_mode=ParseMode.HTML, reply_markup=kb)
            else:
                await q.get_bot().send_message(q.message.chat_id, txt,
                    parse_mode=ParseMode.HTML, reply_markup=kb)
        except: pass'''

m = re.search(r"^async def edit_msg\([^)]*\):\s*$", src, re.MULTILINE)
if m:
    nxt = re.search(r"^(?:async def |def |class )", src[m.end():], re.MULTILINE)
    end = m.end() + nxt.start() if nxt else len(src)
    src = src[:m.start()] + new_edit + "\n\n\n" + src[end:]
    changed.append("edit_msg")

# 3. cmd_share: gui text (khong anh) - giu nguyen, khong doi

p.write_text(src, encoding="utf-8")
ast.parse(src)
print("[+] OK. Changed: " + ", ".join(changed))