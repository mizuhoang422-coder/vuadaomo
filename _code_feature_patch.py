import ast, re, sys
from pathlib import Path

p = Path.home() / "Desktop" / "vuadaomo" / "vuadaomo.py"
src = p.read_text(encoding="utf-8")
changed = []

def replace_func(src, name, new_src):
    m = re.search(rf'^async def {name}\([^)]*\):\s*$', src, re.MULTILINE)
    if not m:
        m = re.search(rf'^def {name}\([^)]*\):\s*$', src, re.MULTILINE)
    if not m:
        return src, False
    start = m.start()
    nxt = re.search(r'^(async def |def |class )', src[m.end():], re.MULTILINE)
    end = m.end() + nxt.start() if nxt else len(src)
    return src[:start] + new_src.rstrip() + "\n\n\n" + src[end:], True

# ---- 1. CHANNELS ----
if 'CHANNELS = ' not in src:
    src = src.replace('CHANNEL = "tinggg999"',
                      'CHANNELS = ["tinggg999", "chat_daumo99"]')
    changed.append("CHANNELS")

# ---- 2. REDEEMED + migrate ----
if 'REDEEMED = ' not in src:
    old = 'USED = set(_load(CODE_FILE, []))'
    new = ('_raw_codes = _load(CODE_FILE, {})\n'
           'if isinstance(_raw_codes, list):\n'
           '    _raw_codes = {c: [] for c in _raw_codes}\n'
           '    _save(CODE_FILE, _raw_codes)\n'
           'REDEEMED = _raw_codes  # {code: [ten_acc_da_nhap]}')
    src = src.replace(old, new)
    changed.append("REDEEMED")

# ---- 3. Watcher rewrite neu chua ----
if '"watcher] joined "' not in src:
    new_watch = '''async def watcher_loop(app):
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
            print("[watcher] " + code + " -> " + str(len(todo)) + " acc chua nhap")
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
                            print("[watcher] " + code + " OK cho " + nm)
                    except: pass
    print("[watcher] listening " + ", ".join(CHANNELS))
    await client.run_until_disconnected()'''
    src, ok = replace_func(src, "watcher_loop", new_watch)
    if ok: changed.append("watcher_loop")

# ---- 4. main_caption: len(USED) -> REDEEMED ----
src = src.replace('str(len(USED))', 'str(len(REDEEMED))')

# ---- 5. Them cac function moi neu chua co ----
if "async def cb_code_menu" not in src:
    new_funcs = '''

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
    txt = ("📜 <b>QUAN LY CODE</b>\\n"
           "━━━━━━━━━━━━━━━━━━━\\n"
           "📊 Tong code da bat: <b>" + str(len(REDEEMED)) + "</b>\\n"
           "📱 Acc cua ban: <b>" + str(len(names)) + "</b>\\n"
           "⏳ Code chua nhap het: <b>" + str(pending) + "</b>\\n"
           "━━━━━━━━━━━━━━━━━━━\\n")
    recent = list(REDEEMED.items())[-15:]
    if recent:
        txt += "\\n<b>15 code gan nhat:</b>\\n"
        for code, accs in reversed(recent):
            txt += "<code>" + code + "</code>  ->  " + str(len(accs)) + " acc\\n"
    else:
        txt += "\\n<i>Chua co code nao</i>"
    wlabel = "⏹ Tat theo doi" if (WATCH and not WATCH.done()) else "▶️ Bat theo doi"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(wlabel, callback_data="code_tog")],
        [InlineKeyboardButton("🔄 Nhap lai code con thieu", callback_data="code_retry")],
        [InlineKeyboardButton("📤 Export backup", callback_data="code_export")],
        [InlineKeyboardButton("🔙 Quay lai", callback_data="menu")],
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
                    else:
                        fail_n += 1
                else:
                    fail_n += 1
            except:
                fail_n += 1
    await q.answer("Thu " + str(tried) + " lan - OK: " + str(ok_n) + " - Fail: " + str(fail_n), show_alert=True)
    await cb_code_menu(u, c)


async def cb_code_export(u, c):
    q = u.callback_query; await q.answer("Dang tao file...")
    import io
    import json as _json
    data = _json.dumps(REDEEMED, indent=2, ensure_ascii=False)
    bio = io.BytesIO(data.encode("utf-8"))
    bio.name = "codes_backup.json"
    try:
        await c.bot.send_document(q.message.chat_id, bio, caption="📤 Backup codes")
    except Exception as e:
        await q.answer("Loi: " + str(e), show_alert=True)


async def cmd_codes(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    names = user_accs(uid)
    if not REDEEMED:
        await u.message.reply_text("Chua co code nao"); return
    lines = ["📜 LICH SU CODE", "---", ""]
    for code, accs in list(REDEEMED.items())[-30:]:
        chua = [n for n in names if n not in accs]
        mark = "" if not chua else "  (con " + str(len(chua)) + " acc chua)"
        lines.append(code + " -> " + str(len(accs)) + " acc" + mark)
    await u.message.reply_text("\\n".join(lines))


'''
    # Chen truoc async def cmd_start
    if "async def cmd_start(" in src:
        src = src.replace("async def cmd_start(", new_funcs + "async def cmd_start(", 1)
        changed.append("code funcs")

# ---- 6. Sua kb_main - nut Auto code -> Quan ly code ----
old_btn = '[InlineKeyboardButton("📊  Live view", callback_data="live"),\n         InlineKeyboardButton("🎁  Auto code", callback_data="code_tog")],'
new_btn = '[InlineKeyboardButton("📊  Live view", callback_data="live"),\n         InlineKeyboardButton("📜  Quan ly code", callback_data="code_menu")],'
if old_btn in src:
    src = src.replace(old_btn, new_btn)
    changed.append("kb_main")

# ---- 7. Them handler ----
if 'pattern="^code_menu$"' not in src:
    old_h = '    app.add_handler(CallbackQueryHandler(cb_code_tog, pattern="^code_tog$"))'
    new_h = ('    app.add_handler(CallbackQueryHandler(cb_code_tog, pattern="^code_tog$"))\n'
             '    app.add_handler(CallbackQueryHandler(cb_code_menu, pattern="^code_menu$"))\n'
             '    app.add_handler(CallbackQueryHandler(cb_code_retry, pattern="^code_retry$"))\n'
             '    app.add_handler(CallbackQueryHandler(cb_code_export, pattern="^code_export$"))\n'
             '    app.add_handler(CommandHandler("codes", cmd_codes))')
    src = src.replace(old_h, new_h)
    changed.append("handlers")

# ---- 8. Auto-retro khi acc farm ----
# Trong farm_loop, sau login va truoc cac task khac, retro code chua nhap
marker = 'if f.get("mine") and not u.get("is_mining"):'
retro_block = '''# auto-retro: nap code cu ma acc chua nhap (gioi han 5/vong)
            if REDEEMED:
                retro_n = 0
                for code, accs in list(REDEEMED.items()):
                    if name in accs: continue
                    try:
                        rr = await asyncio.to_thread(api, name, "/api/redeem-code", {"code": code})
                        if rr and rr.status_code == 200:
                            jj = rr.json()
                            if jj.get("success"):
                                accs.append(name); _save(CODE_FILE, REDEEMED)
                                st = a.setdefault("stats", {})
                                st["redeem"] = st.get("redeem", 0) + 1
                                _save(ACC_FILE, ACCS)
                                print("[retro] " + name + " " + code)
                    except: pass
                    retro_n += 1
                    if retro_n >= 5: break
            '''
if "[retro]" not in src:
    if marker in src:
        src = src.replace(marker, retro_block + "            " + marker, 1)
        changed.append("auto-retro")

# ---- 9. Check USED khong con ----
if re.search(r'\bUSED\b', src):
    print("[!] Con USED trong source:")
    for i, line in enumerate(src.split("\\n"), 1):
        if re.search(r'\\bUSED\\b', line):
            print("  L" + str(i) + ": " + line.strip())
    sys.exit(1)

# ---- 10. Check _save(CODE_FILE, list(...)) ----
if "_save(CODE_FILE, list(" in src:
    print("[!] Con _save(CODE_FILE, list(...) - se sai logic")
    sys.exit(1)

p.write_text(src, encoding="utf-8")
ast.parse(src)
print("[+] OK. Changed: " + ", ".join(changed))