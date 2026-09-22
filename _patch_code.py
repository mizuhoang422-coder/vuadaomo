import ast, re, sys
from pathlib import Path

p = Path.home() / "Desktop" / "vuadaomo" / "vuadaomo.py"
src = p.read_text(encoding="utf-8")
changed = []

def replace_func(src, name, new_src):
    m = re.search(rf"^(?:async )?def {name}\([^)]*\):\s*$", src, re.MULTILINE)
    if not m: return src, False
    start = m.start()
    nxt = re.search(r"^(?:async def |def |class )", src[m.end():], re.MULTILINE)
    end = m.end() + nxt.start() if nxt else len(src)
    return src[:start] + new_src.rstrip() + "\n\n\n" + src[end:], True

if "CHANNELS = " not in src:
    src = src.replace('CHANNEL = "tinggg999"', 'CHANNELS = ["tinggg999", "chat_daumo99"]')
    changed.append("CHANNELS")

if "REDEEMED = " not in src:
    old = "USED = set(_load(CODE_FILE, []))"
    new = ("_rc = _load(CODE_FILE, {})\n"
           "if isinstance(_rc, list):\n"
           "    _rc = {c: [] for c in _rc}\n"
           "    _save(CODE_FILE, _rc)\n"
           "REDEEMED = _rc")
    src = src.replace(old, new)
    changed.append("REDEEMED")

if 'joined "' not in src:
    nw = '''async def watcher_loop(app):
    if not ACCS: return
    fn = None
    for n, a in ACCS.items():
        if a.get("session_string"): fn = n; break
    if not fn: return
    client = None
    try:
        client = TelegramClient(StringSession(ACCS[fn]["session_string"]), API_ID, API_HASH)
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect(); return
        ents = []
        for ch in CHANNELS:
            try:
                e = await client.get_entity(ch)
                ents.append(e)
                print("[watcher] joined " + ch)
            except Exception as ex:
                print("[watcher] skip " + ch + ": " + str(ex))
        if not ents:
            await client.disconnect(); return
    except Exception as e:
        print("[watcher] " + str(e))
        if client:
            try: await client.disconnect()
            except: pass
        return

    @client.on(events.NewMessage(chats=ents))
    async def on_msg(ev):
        text = ev.message.message or ""
        for code in re.findall(r"VUADAUMO_[A-Z0-9]{5,}", text.upper()):
            already = REDEEMED.setdefault(code, [])
            todo = [n for n in list(ACCS.keys()) if n not in already]
            if not todo: continue
            print("[watcher] " + code + " -> " + str(len(todo)) + " acc")
            for nm in todo:
                r = await asyncio.to_thread(api, nm, "/api/redeem-code", {"code": code})
                if r and r.status_code == 200:
                    try:
                        j = r.json()
                        if j.get("success"):
                            already.append(nm); _save(CODE_FILE, REDEEMED)
                            st = ACCS[nm].setdefault("stats", {})
                            st["redeem"] = st.get("redeem", 0) + 1
                            _save(ACC_FILE, ACCS)
                            print("[watcher] " + code + " OK " + nm)
                    except: pass
    print("[watcher] listening " + ", ".join(CHANNELS))
    await client.run_until_disconnected()'''
    src, ok = replace_func(src, "watcher_loop", nw)
    if ok: changed.append("watcher")

src = src.replace("str(len(USED))", "str(len(REDEEMED))")

if "async def cb_code_menu" not in src:
    nf = '''

async def cb_code_menu(u, c):
    q = u.callback_query; await q.answer()
    uid = u.effective_user.id
    names = user_accs(uid)
    pending = 0
    for code, accs in REDEEMED.items():
        for n in names:
            if n not in accs:
                pending += 1
                break
    txt = ("<b>QUAN LY CODE</b>\\n"
           "----------\\n"
           "Tong code: <b>" + str(len(REDEEMED)) + "</b>\\n"
           "Acc cua ban: <b>" + str(len(names)) + "</b>\\n"
           "Code chua nhap het: <b>" + str(pending) + "</b>\\n"
           "----------\\n")
    recent = list(REDEEMED.items())[-15:]
    if recent:
        txt += "\\n<b>15 code gan nhat:</b>\\n"
        for code, accs in reversed(recent):
            txt += "<code>" + code + "</code> -> " + str(len(accs)) + " acc\\n"
    else:
        txt += "\\n<i>Chua co code nao</i>"
    wlabel = "Tat theo doi" if (WATCH and not WATCH.done()) else "Bat theo doi"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(wlabel, callback_data="code_tog")],
        [InlineKeyboardButton("Nhap lai code con thieu", callback_data="code_retry")],
        [InlineKeyboardButton("Export backup", callback_data="code_export")],
        [InlineKeyboardButton("Quay lai", callback_data="menu")],
    ])
    await edit_msg(q, txt, kb)


async def cb_code_retry(u, c):
    q = u.callback_query; await q.answer("Dang thu lai...")
    uid = u.effective_user.id
    names = user_accs(uid)
    if not names:
        await q.answer("Chua co acc", show_alert=True); return
    ok_n = 0; fail_n = 0; tried = 0
    for code, accs in list(REDEEMED.items()):
        for n in names:
            if n in accs: continue
            tried += 1
            try:
                r = await asyncio.to_thread(api, n, "/api/redeem-code", {"code": code})
                if r and r.status_code == 200:
                    j = r.json()
                    if j.get("success"):
                        accs.append(n); _save(CODE_FILE, REDEEMED)
                        st = ACCS[n].setdefault("stats", {})
                        st["redeem"] = st.get("redeem", 0) + 1
                        _save(ACC_FILE, ACCS)
                        ok_n += 1
                    else: fail_n += 1
                else: fail_n += 1
            except: fail_n += 1
    await q.answer("Thu " + str(tried) + " - OK " + str(ok_n) + " - Fail " + str(fail_n), show_alert=True)
    await cb_code_menu(u, c)


async def cb_code_export(u, c):
    q = u.callback_query; await q.answer("Dang tao...")
    import io, json as _j
    data = _j.dumps(REDEEMED, indent=2, ensure_ascii=False)
    bio = io.BytesIO(data.encode("utf-8"))
    bio.name = "codes_backup.json"
    try:
        await c.bot.send_document(q.message.chat_id, bio, caption="Backup codes")
    except Exception as e:
        await q.answer("Loi: " + str(e), show_alert=True)


async def cmd_codes(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    names = user_accs(uid)
    if not REDEEMED:
        await u.message.reply_text("Chua co code nao"); return
    lines = ["LICH SU CODE", "---", ""]
    for code, accs in list(REDEEMED.items())[-30:]:
        chua = [n for n in names if n not in accs]
        mk = "" if not chua else "  (con " + str(len(chua)) + " acc)"
        lines.append(code + " -> " + str(len(accs)) + " acc" + mk)
    await u.message.reply_text("\\n".join(lines))


'''
    src = src.replace("async def cmd_start(", nf + "async def cmd_start(", 1)
    changed.append("code funcs")

old_btn = '[InlineKeyboardButton("📊  Live view", callback_data="live"),\n         InlineKeyboardButton("🎁  Auto code", callback_data="code_tog")],'
new_btn = '[InlineKeyboardButton("📊  Live view", callback_data="live"),\n         InlineKeyboardButton("📜  Quan ly code", callback_data="code_menu")],'
if old_btn in src:
    src = src.replace(old_btn, new_btn)
    changed.append("kb_main")

if 'pattern="^code_menu$"' not in src:
    old_h = '    app.add_handler(CallbackQueryHandler(cb_code_tog, pattern="^code_tog$"))'
    new_h = ('    app.add_handler(CallbackQueryHandler(cb_code_tog, pattern="^code_tog$"))\n'
             '    app.add_handler(CallbackQueryHandler(cb_code_menu, pattern="^code_menu$"))\n'
             '    app.add_handler(CallbackQueryHandler(cb_code_retry, pattern="^code_retry$"))\n'
             '    app.add_handler(CallbackQueryHandler(cb_code_export, pattern="^code_export$"))\n'
             '    app.add_handler(CommandHandler("codes", cmd_codes))')
    src = src.replace(old_h, new_h)
    changed.append("handlers")

# FIX: retro block phai cung indent voi dong if f.get("mine") - 12 spaces
marker = '            if f.get("mine") and not u.get("is_mining"):'
if "[retro]" not in src and marker in src:
    # 12 spaces cho tat ca cac dong
    rb = (
        "            if REDEEMED:\n"
        "                rn = 0\n"
        "                for code, accs in list(REDEEMED.items()):\n"
        "                    if name in accs: continue\n"
        "                    try:\n"
        "                        rr = await asyncio.to_thread(api, name, \"/api/redeem-code\", {\"code\": code})\n"
        "                        if rr and rr.status_code == 200:\n"
        "                            jj = rr.json()\n"
        "                            if jj.get(\"success\"):\n"
        "                                accs.append(name); _save(CODE_FILE, REDEEMED)\n"
        "                                st = a.setdefault(\"stats\", {})\n"
        "                                st[\"redeem\"] = st.get(\"redeem\", 0) + 1\n"
        "                                _save(ACC_FILE, ACCS)\n"
        "                                print(\"[retro] \" + name + \" \" + code)\n"
        "                    except: pass\n"
        "                    rn += 1\n"
        "                    if rn >= 5: break\n"
    )
    src = src.replace(marker, rb + marker, 1)
    changed.append("auto-retro")

if re.search(r"\bUSED\b", src):
    print("[!] Con USED:")
    for i, ln in enumerate(src.split("\n"), 1):
        if re.search(r"\bUSED\b", ln): print("  L" + str(i) + ": " + ln.strip())
    sys.exit(2)

if "_save(CODE_FILE, list(" in src:
    print("[!] Con _save(CODE_FILE, list(...)"); sys.exit(3)

p.write_text(src, encoding="utf-8")
ast.parse(src)
print("[+] OK. Changed: " + ", ".join(changed))