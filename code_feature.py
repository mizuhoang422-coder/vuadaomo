# code_feature.py - module quan ly code (doc lap voi vuadaomo.py)
# install(app, ctx) - dang ky handler; watcher_loop - theo doi kenh;
# try_retro(name, a) - nap code cu cho acc chua nhap

import re, asyncio, io, json
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CommandHandler
from telethon import TelegramClient, events
from telethon.sessions import StringSession

CHANNELS = ["tinggg999", "chat_daumo99"]
_CTX = None


def install(app, ctx):
    global _CTX
    _CTX = ctx
    _migrate()
    app.add_handler(CommandHandler("codes", cmd_codes))
    app.add_handler(CommandHandler("redeem", cmd_redeem))
    app.add_handler(CallbackQueryHandler(cb_code_menu, pattern="^code_menu$"))
    app.add_handler(CallbackQueryHandler(cb_code_retry, pattern="^code_retry$"))
    app.add_handler(CallbackQueryHandler(cb_code_export, pattern="^code_export$"))
    print("[code_feature] installed, channels=" + ",".join(CHANNELS))


def _c(k, d=None):
    if _CTX is None: return d
    return _CTX.get(k, d)


def _redeemed():
    return _c("REDEEMED", {})


def _migrate():
    cf = _c("CODE_FILE"); lj = _c("_load"); sj = _c("_save")
    if not (cf and lj and sj): return
    raw = lj(cf, {})
    if isinstance(raw, list):
        sj(cf, {c: [] for c in raw})
        print("[code_feature] migrated " + str(len(raw)) + " codes")


async def watcher_loop(app):
    ACCS = _c("ACCS", {})
    if not ACCS: return
    fn = None
    for n, a in ACCS.items():
        if a.get("session_string"): fn = n; break
    if not fn: return
    client = None
    try:
        client = TelegramClient(StringSession(ACCS[fn]["session_string"]), _c("API_ID"), _c("API_HASH"))
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
            await _redeem_all(code)
    print("[watcher] listening " + ", ".join(CHANNELS))
    await client.run_until_disconnected()


async def _redeem_all(code):
    REDEEMED = _redeemed(); ACCS = _c("ACCS", {})
    api = _c("api"); cf = _c("CODE_FILE"); af = _c("ACC_FILE"); sj = _c("_save")
    if not (api and cf and af and sj): return
    already = REDEEMED.setdefault(code, [])
    todo = [n for n in list(ACCS.keys()) if n not in already]
    if not todo: return
    print("[watcher] " + code + " -> " + str(len(todo)) + " acc")
    for nm in todo:
        try:
            r = await asyncio.to_thread(api, nm, "/api/redeem-code", {"code": code})
            if r and r.status_code == 200:
                j = r.json()
                if j.get("success"):
                    already.append(nm); sj(cf, REDEEMED)
                    st = ACCS[nm].setdefault("stats", {})
                    st["redeem"] = st.get("redeem", 0) + 1
                    sj(af, ACCS)
                    print("[watcher] " + code + " OK " + nm)
        except Exception as e:
            print("[watcher] " + nm + ": " + str(e))


async def try_retro(name, a):
    REDEEMED = _redeemed()
    if not REDEEMED: return
    api = _c("api"); cf = _c("CODE_FILE"); af = _c("ACC_FILE"); sj = _c("_save")
    ACCS = _c("ACCS", {})
    if not (api and cf and af and sj): return
    n = 0
    for code, accs in list(REDEEMED.items()):
        if name in accs: continue
        try:
            r = await asyncio.to_thread(api, name, "/api/redeem-code", {"code": code})
            if r and r.status_code == 200:
                j = r.json()
                if j.get("success"):
                    accs.append(name); sj(cf, REDEEMED)
                    st = a.setdefault("stats", {})
                    st["redeem"] = st.get("redeem", 0) + 1
                    sj(af, ACCS)
                    print("[retro] " + name + " " + code)
        except: pass
        n += 1
        if n >= 5: break


async def cmd_codes(u, c):
    names = _c("user_accs")(u.effective_user.id)
    REDEEMED = _redeemed()
    if not REDEEMED:
        await u.message.reply_text("Chua co code nao"); return
    lines = ["LICH SU CODE", "---", ""]
    for code, accs in list(REDEEMED.items())[-30:]:
        chua = [n for n in names if n not in accs]
        mk = "" if not chua else "  (con " + str(len(chua)) + " acc)"
        lines.append(code + " -> " + str(len(accs)) + " acc" + mk)
    await u.message.reply_text("\n".join(lines))


async def cmd_redeem(u, c):
    parts = (u.message.text or "").strip().split(" ", 1)
    if len(parts) < 2:
        await u.message.reply_text("Cu phap: /redeem VUADAUMO_XXXXX"); return
    code = parts[1].strip().upper()
    if not re.match(r"^VUADAUMO_[A-Z0-9]{5,}$", code):
        await u.message.reply_text("Format sai (VUADAUMO_...)"); return
    names = _c("user_accs")(u.effective_user.id)
    if not names:
        await u.message.reply_text("Chua co acc"); return
    REDEEMED = _redeemed(); already = REDEEMED.setdefault(code, [])
    todo = [n for n in names if n not in already]
    if not todo:
        await u.message.reply_text("Tat ca acc da nhap code nay"); return
    msg = await u.message.reply_text("Dang nhap " + code + " cho " + str(len(todo)) + " acc...")
    api = _c("api"); cf = _c("CODE_FILE"); af = _c("ACC_FILE"); sj = _c("_save")
    ACCS = _c("ACCS", {}); ok_n = 0; fail_n = 0
    for n in todo:
        try:
            r = await asyncio.to_thread(api, n, "/api/redeem-code", {"code": code})
            if r and r.status_code == 200:
                j = r.json()
                if j.get("success"):
                    already.append(n); sj(cf, REDEEMED)
                    st = ACCS[n].setdefault("stats", {})
                    st["redeem"] = st.get("redeem", 0) + 1
                    sj(af, ACCS); ok_n += 1
                else: fail_n += 1
            else: fail_n += 1
        except: fail_n += 1
    await msg.edit_text("OK " + str(ok_n) + " / Fail " + str(fail_n), reply_markup=_c("kb_main")())


async def cb_code_menu(u, c):
    q = u.callback_query; await q.answer()
    REDEEMED = _redeemed()
    names = _c("user_accs")(u.effective_user.id)
    pending = 0
    for code, accs in REDEEMED.items():
        for n in names:
            if n not in accs:
                pending += 1; break
    txt = ("<b>QUAN LY CODE</b>\n----------\n"
           "Tong code: <b>" + str(len(REDEEMED)) + "</b>\n"
           "Acc cua ban: <b>" + str(len(names)) + "</b>\n"
           "Code chua nhap het: <b>" + str(pending) + "</b>\n----------\n")
    recent = list(REDEEMED.items())[-15:]
    if recent:
        txt += "\n<b>15 code gan nhat:</b>\n"
        for code, accs in reversed(recent):
            txt += "<code>" + code + "</code> -> " + str(len(accs)) + " acc\n"
    else:
        txt += "\n<i>Chua co code nao</i>"
    WATCH = _c("WATCH")
    try: on = bool(WATCH and not WATCH.done())
    except: on = False
    wlabel = "Tat theo doi" if on else "Bat theo doi"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(wlabel, callback_data="code_tog")],
        [InlineKeyboardButton("Nhap lai code con thieu", callback_data="code_retry")],
        [InlineKeyboardButton("Export backup", callback_data="code_export")],
        [InlineKeyboardButton("Quay lai", callback_data="menu")],
    ])
    await _c("edit_msg")(q, txt, kb)


async def cb_code_retry(u, c):
    q = u.callback_query; await q.answer("Dang thu lai...")
    names = _c("user_accs")(u.effective_user.id)
    if not names:
        await q.answer("Chua co acc", show_alert=True); return
    REDEEMED = _redeemed()
    api = _c("api"); cf = _c("CODE_FILE"); af = _c("ACC_FILE"); sj = _c("_save")
    ACCS = _c("ACCS", {}); ok_n = 0; fail_n = 0; tried = 0
    for code, accs in list(REDEEMED.items()):
        for n in names:
            if n in accs: continue
            tried += 1
            try:
                r = await asyncio.to_thread(api, n, "/api/redeem-code", {"code": code})
                if r and r.status_code == 200:
                    j = r.json()
                    if j.get("success"):
                        accs.append(n); sj(cf, REDEEMED)
                        st = ACCS[n].setdefault("stats", {})
                        st["redeem"] = st.get("redeem", 0) + 1
                        sj(af, ACCS); ok_n += 1
                    else: fail_n += 1
                else: fail_n += 1
            except: fail_n += 1
    await q.answer("Thu " + str(tried) + " - OK " + str(ok_n) + " - Fail " + str(fail_n), show_alert=True)
    await cb_code_menu(u, c)


async def cb_code_export(u, c):
    q = u.callback_query; await q.answer("Dang tao...")
    data = json.dumps(_redeemed(), indent=2, ensure_ascii=False)
    bio = io.BytesIO(data.encode("utf-8"))
    bio.name = "codes_backup.json"
    try:
        await c.bot.send_document(q.message.chat_id, bio, caption="Backup codes")
    except Exception as e:
        await q.answer("Loi: " + str(e), show_alert=True)