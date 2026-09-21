import ast, sys
from pathlib import Path

p = Path.home() / "Desktop" / "vuadaomo" / "vuadaomo.py"
src = p.read_text(encoding="utf-8")

def repl_func(src, name, new_code):
    try: tree = ast.parse(src)
    except SyntaxError as e:
        print(f"[-] syntax loi truoc khi patch: {e}"); sys.exit(1)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            lines = src.split("\n")
            s = node.lineno - 1
            e = node.end_lineno
            return "\n".join(lines[:s]) + "\n" + new_code + "\n" + "\n".join(lines[e:])
    print(f"[*] khong tim thay {name}")
    return src

MAIN_CAP = """def main_caption():
    nn = len(A)
    on = 0
    for w in WORKERS.values():
        try:
            if not w.done(): on += 1
        except: pass
    try:
        wr = "BẬT" if (WATCH and not WATCH.done()) else "TẮT"
    except: wr = "TẮT"
    return (
        "<b>🔥 A1ZTUS BYPASS</b>\\n"
        "<i>⚡ Trung tâm điều khiển Vua Dầu Mỏ</i>\\n"
        "━━━━━━━━━━━━━━━━━━━\\n"
        "<b>📊 TỔNG QUAN</b>\\n"
        "👥 Tài khoản: <b>" + str(nn) + "</b>\\n"
        "▶️ Đang farm: <b>" + str(on) + "</b>\\n"
        "🎁 Code đã dùng: <b>" + str(len(UC)) + "</b>\\n"
        "📡 Theo dõi code: <b>" + wr + "</b>\\n"
        "━━━━━━━━━━━━━━━━━━━\\n"
        "<i>💡 Chọn chức năng bên dưới</i>"
    )"""

KB_MAIN = """def kb_main():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕  Thêm tài khoản", callback_data="add"),
         InlineKeyboardButton("📋  Danh sách acc", callback_data="panel_list")],
        [InlineKeyboardButton("▶️  Bật tất cả", callback_data="start_all"),
         InlineKeyboardButton("⏹  Tắt tất cả", callback_data="stop_all")],
        [InlineKeyboardButton("📊  Live view", callback_data="live"),
         InlineKeyboardButton("🎁  Auto code", callback_data="code_tog")],
        [InlineKeyboardButton("🔄  Làm mới tất cả", callback_data="rf_all"),
         InlineKeyboardButton("🗑  Xóa acc", callback_data="del_list")],
    ])"""

KB_PANEL = """def kb_panel(n, f, run):
    def b(k, lb):
        v = f.get(k, False)
        mark = "🟢" if v else "🔴"
        return InlineKeyboardButton(mark + " " + lb, callback_data="tog:" + n + ":" + k)
    rb = InlineKeyboardButton("⏹  Dừng farm", callback_data="stop:" + n) if run else InlineKeyboardButton("▶️  Bắt đầu farm", callback_data="start:" + n)
    return InlineKeyboardMarkup([
        [b("mine", "⛏️ Đào mỏ"), b("claim", "💰 Thu hoạch")],
        [b("watch", "📺 Xem video"), b("box", "📦 Mở hộp")],
        [b("craft", "🎫 Ghép vé"), b("spin", "🎰 Vòng quay")],
        [b("exchange", "💱 Đổi VND"), b("upgrade", "⬆️ Nâng cấp")],
        [rb],
        [InlineKeyboardButton("💰  Rút tiền", callback_data="wd:" + n),
         InlineKeyboardButton("⬆️  Nâng cấp nhanh", callback_data="up:" + n)],
        [InlineKeyboardButton("🔄  Làm mới", callback_data="rf:" + n),
         InlineKeyboardButton("🔙  Quay lại", callback_data="menu")],
    ])"""

PANEL_TEXT = """def panel_text(n):
    a = A.get(n, {})
    u = a.get("user", {})
    try: run = n in WORKERS and not WORKERS[n].done()
    except: run = False
    st = "🟢 <b>ĐANG CHẠY</b>" if run else "🔴 <b>ĐANG DỪNG</b>"
    s = a.get("stats", {})
    oil = fx(u.get("oil_balance", 0))
    vnd = u.get("vnd_balance", 0)
    spd = u.get("speed_lvl", 0)
    cap = u.get("capacity_lvl", 0)
    tkt = u.get("tickets", 0)
    shd = u.get("shards", 0)
    box = u.get("mystery_boxes", 0)
    ph = a.get("phone", "?")
    un = u.get("username", "?")
    return (
        "👤 <b>" + n.upper() + "</b>\\n"
        "📱 " + str(ph) + "\\n"
        "🆔 @" + str(un) + "\\n"
        "━━━━━━━━━━━━━━━━━━━\\n"
        "💰 Dầu: <b>" + str(oil) + "</b>\\n"
        "💵 VND: <b>" + str(vnd) + "</b>\\n"
        "⚡ Tốc độ: <b>" + str(spd) + "</b>   📦 Sức chứa: <b>" + str(cap) + "</b>\\n"
        "🎫 Vé: <b>" + str(tkt) + "</b>   💎 Mảnh: <b>" + str(shd) + "</b>   🎁 Hộp: <b>" + str(box) + "</b>\\n"
        "━━━━━━━━━━━━━━━━━━━\\n"
        + st + "\\n"
        "<i>📊 " + str(s.get("claim",0)) + " thu · " + str(s.get("watch",0)) + " video · "
        + str(s.get("box",0)) + " hộp · " + str(s.get("spin",0)) + " quay · "
        + str(s.get("exchange",0)) + " đổi · " + str(s.get("redeem",0)) + " code</i>"
    )"""

CMD_START = """async def cmd_start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not ok(u.effective_user.id):
        await u.message.reply_text("⛔ Bạn không có quyền truy cập")
        return
    try:
        await u.message.reply_photo(PHOTO, caption=main_caption(), parse_mode=ParseMode.HTML, reply_markup=kb_main())
    except Exception:
        await u.message.reply_text(main_caption(), parse_mode=ParseMode.HTML, reply_markup=kb_main())"""

EDIT = """async def edit(q, txt, kb):
    try:
        if q.message.photo:
            await q.edit_message_caption(caption=txt, parse_mode=ParseMode.HTML, reply_markup=kb)
        else:
            await q.edit_message_text(txt, parse_mode=ParseMode.HTML, reply_markup=kb)
    except Exception as e:
        msg = str(e)
        if "message is not modified" in msg:
            return
        try:
            await q.message.delete()
        except Exception:
            pass
        try:
            await q.get_bot().send_photo(q.message.chat_id, PHOTO, caption=txt, parse_mode=ParseMode.HTML, reply_markup=kb)
        except Exception:
            try:
                await q.get_bot().send_message(q.message.chat_id, txt, parse_mode=ParseMode.HTML, reply_markup=kb)
            except Exception:
                pass"""

src = repl_func(src, "kb_main", KB_MAIN)
src = repl_func(src, "kb_panel", KB_PANEL)
src = repl_func(src, "panel_text", PANEL_TEXT)
src = repl_func(src, "cmd_start", CMD_START)
src = repl_func(src, "edit", EDIT)

if "def main_caption(" not in src:
    src = src.replace("def kb_main():", MAIN_CAP + "\n\n\n" + "def kb_main():", 1)

src = src.replace("await edit(q, BANNER, kb_main())", "await edit(q, main_caption(), kb_main())")
src = src.replace("caption=BANNER, reply_markup=kb_main()", "caption=main_caption(), parse_mode=ParseMode.HTML, reply_markup=kb_main()")

p.write_text(src, encoding="utf-8")
ast.parse(src)
print("[+] patched + syntax ok")