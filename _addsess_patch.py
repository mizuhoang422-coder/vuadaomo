import ast
from pathlib import Path
p = Path.home() / "Desktop" / "vuadaomo" / "vuadaomo.py"
src = p.read_text(encoding="utf-8")

# 1. Them conversation state
src = src.replace(
    "S_NAME, S_PHONE, S_OTP, S_PWD = range(4)",
    "S_NAME, S_PHONE, S_OTP, S_PWD = range(4)\nAS_NAME, AS_PHONE, AS_SESS = range(10, 13)"
)

# 2. Them 3 handler + cancel cho /addsession
new_funcs = '''

async def addsess_start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text("➕ <b>THÊM BẰNG SESSION</b>\\n\\nNhập tên acc (vd: FOX):", parse_mode=ParseMode.HTML)
    return AS_NAME

async def addsess_name(u: Update, c: ContextTypes.DEFAULT_TYPE):
    n = u.message.text.strip()
    if not n or n in ACCS:
        await u.message.reply_text("❌ Trùng/trống. Nhập lại:"); return AS_NAME
    c.user_data["asn"] = n
    await u.message.reply_text("📱 Nhập SĐT (+84...):")
    return AS_PHONE

async def addsess_phone(u: Update, c: ContextTypes.DEFAULT_TYPE):
    ph = u.message.text.strip()
    if not ph.startswith("+"):
        await u.message.reply_text("❌ Cần bắt đầu +84. Nhập lại:"); return AS_PHONE
    c.user_data["asp"] = ph
    await u.message.reply_text(
        "📋 Paste session string vào đây.\\n\\n"
        "⚠️ Bot sẽ <b>XÓA TIN NHẮN</b> chứa session ngay sau khi lưu.\\n\\n"
        "<i>Lấy session: chạy get_session.py trên máy tính, login 1 lần, copy chuỗi dài.</i>",
        parse_mode=ParseMode.HTML)
    return AS_SESS

async def addsess_sess(u: Update, c: ContextTypes.DEFAULT_TYPE):
    s = u.message.text.strip()
    n = c.user_data.get("asn"); ph = c.user_data.get("asp")
    try: await u.message.delete()
    except: pass
    if not s or len(s) < 50:
        await u.message.reply_text("❌ Session quá ngắn. Bấm /addsession lại."); return ConversationHandler.END
    msg = await u.message.reply_text("⏳ Đang kiểm tra session...")
    try:
        test = await fetch_initdata(s)
    except Exception as e:
        test = None
    if not test:
        await msg.edit_text("❌ Session không hoạt động hoặc không lấy được initData.")
        return ConversationHandler.END
    ACCS[n] = {
        "phone": ph, "session_string": s, "owner": u.effective_user.id,
        "created": datetime.now().isoformat(),
        "flags": {"mine": True, "claim": True, "watch": True, "box": True, "craft": True, "spin": True, "exchange": True, "upgrade": True},
        "user": {}, "stats": {}, "cd": {},
        "init_data": test, "init_ts": time.time(),
    }
    _save(ACC_FILE, ACCS)
    await msg.edit_text("✅ Đã thêm <b>" + n + "</b>\\n📡 initData: OK\\n📱 " + ph, parse_mode=ParseMode.HTML, reply_markup=kb_main())
    return ConversationHandler.END

async def addsess_cancel(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text("Đã hủy.")
    return ConversationHandler.END

'''
src = src.replace("async def cmd_start(", new_funcs + "async def cmd_start(", 1)

# 3. Dang ky command /addsession + conversation
src = src.replace(
    '    app.add_handler(CommandHandler("myid", cmd_myid))',
    '    app.add_handler(CommandHandler("myid", cmd_myid))\n'
    '    app.add_handler(CommandHandler("addsession", addsess_start))'
)
src = src.replace(
    '    app.add_handler(conv)',
    '''    conv2 = ConversationHandler(
        entry_points=[CommandHandler("addsession", addsess_start)],
        states={AS_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, addsess_name)],
                AS_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, addsess_phone)],
                AS_SESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, addsess_sess)]},
        fallbacks=[CommandHandler("cancel", addsess_cancel)])
    app.add_handler(conv)
    app.add_handler(conv2)'''
)

# 4. Them nut "Them bang session" vao menu
src = src.replace(
    '        [InlineKeyboardButton("🔗  Chia sẻ bot", callback_data="share_help"),\n         InlineKeyboardButton("🆔  ID của tôi", callback_data="myid_help")],',
    '        [InlineKeyboardButton("🔗  Chia sẻ bot", callback_data="share_help"),\n         InlineKeyboardButton("🆔  ID của tôi", callback_data="myid_help")],\n        [InlineKeyboardButton("🔑  Thêm bằng session (khuyến nghị)", callback_data="addsess_help")],'
)

# 5. Handler cho nut addsess_help
if "cb_addsess_help" not in src:
    src = src.replace(
        "async def cb_menu(u, c):",
        '''async def cb_addsess_help(u, c):
    q = u.callback_query; await q.answer()
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Quay lại", callback_data="menu")]])
    txt = ("🔑 <b>THÊM BẰNG SESSION</b>\\n━━━━━━━━━━━━━━━━━━━\\n\\n"
        "Cách này <b>khuyến nghị</b> vì Telegram chặn login OTP từ server nước ngoài.\\n\\n"
        "<b>Các bước:</b>\\n"
        "1️⃣ Trên máy tính, chạy script <code>get_session.py</code>\\n"
        "2️⃣ Login Telegram 1 lần (nhập SĐT + OTP)\\n"
        "3️⃣ Copy chuỗi session string\\n"
        "4️⃣ Gõ lệnh <code>/addsession</code> trong bot này\\n"
        "5️⃣ Nhập tên → SĐT → paste session\\n\\n"
        "<i>Bot tự xóa tin chứa session sau khi lưu.</i>")
    await edit_msg(q, txt, kb)

async def cb_menu(u, c):''',
        1
    )
    src = src.replace(
        '    app.add_handler(CallbackQueryHandler(cb_menu, pattern="^menu$"))',
        '    app.add_handler(CallbackQueryHandler(cb_menu, pattern="^menu$"))\n'
        '    app.add_handler(CallbackQueryHandler(cb_addsess_help, pattern="^addsess_help$"))'
    )

p.write_text(src, encoding="utf-8")
ast.parse(src)
print("[+] patched + syntax OK")