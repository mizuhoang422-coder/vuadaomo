import ast
from pathlib import Path
p = Path.home() / "Desktop" / "vuadaomo" / "vuadaomo.py"
src = p.read_text(encoding="utf-8")

new_cmd = '''

async def cmd_addsession_auto(u: Update, c: ContextTypes.DEFAULT_TYPE):
    """Nhan /addsession_auto name|phone|session tu script local"""
    uid = u.effective_user.id
    txt = (u.message.text or "").strip()
    try: await u.message.delete()
    except: pass
    if " " not in txt:
        await c.bot.send_message(uid, "❌ Sai format"); return
    payload = txt.split(" ", 1)[1]
    segs = payload.split("|", 2)
    if len(segs) < 3:
        await c.bot.send_message(uid, "❌ Format: /addsession_auto name|phone|session"); return
    name, phone, sess = segs[0].strip(), segs[1].strip(), segs[2].strip()
    if not name or not phone or len(sess) < 50:
        await c.bot.send_message(uid, "❌ Field thieu hoac session ngan"); return
    if name in ACCS and not is_owner(uid, name):
        await c.bot.send_message(uid, "❌ Ten trung voi acc cua nguoi khac"); return
    msg = await c.bot.send_message(uid, "⏳ Dang kiem tra session...")
    try: test = await fetch_initdata(sess)
    except Exception as e:
        test = None
    if not test:
        await msg.edit_text("❌ Session khong hoat dong, khong lay duoc initData")
        return
    ACCS[name] = {
        "phone": phone, "session_string": sess, "owner": uid,
        "created": datetime.now().isoformat(),
        "flags": {"mine": True, "claim": True, "watch": True, "box": True, "craft": True, "spin": True, "exchange": True, "upgrade": True},
        "user": {}, "stats": {}, "cd": {},
        "init_data": test, "init_ts": time.time(),
    }
    _save(ACC_FILE, ACCS)
    await msg.edit_text("✅ Da them <b>" + name + "</b>\\n📱 " + phone + "\\n📡 initData: OK", parse_mode=ParseMode.HTML, reply_markup=kb_main())

'''
if "cmd_addsession_auto" not in src:
    src = src.replace("async def cmd_start(", new_cmd + "\nasync def cmd_start(", 1)
    src = src.replace(
        '    app.add_handler(CommandHandler("addsession", addsess_start))',
        '    app.add_handler(CommandHandler("addsession", addsess_start))\n'
        '    app.add_handler(CommandHandler("addsession_auto", cmd_addsession_auto))'
    )

p.write_text(src, encoding="utf-8")
ast.parse(src)
print("[+] bot patched")