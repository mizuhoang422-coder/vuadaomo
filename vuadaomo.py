#!/usr/bin/env python3
# vuadaomo.py - A1ZTUS BYPASS bot
import os, json, re, time, threading, asyncio, urllib.parse
from pathlib import Path
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, ContextTypes, filters)
from telethon import TelegramClient, functions, events
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
import requests

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN: raise SystemExit("BOT_TOKEN env missing")
API_ID = int(os.environ.get("API_ID", "0"))
if not API_ID: raise SystemExit("API_ID env missing")
API_HASH = os.environ.get("API_HASH")
if not API_HASH: raise SystemExit("API_HASH env missing")
ALLOWED = [int(x) for x in os.environ.get("ALLOWED_USERS", "").split(",") if x.strip()]
BASE = "https://vdm.builderminiapp.online"
BOT_USER = "Vua_dau_mo_bot"
CHANNEL = "tinggg999"
MIN_EX = 100000
TTL = 12 * 3600
DD = Path(os.environ.get("DATA_DIR", "/tmp/vdm_bot")); DD.mkdir(parents=True, exist_ok=True)
AF = DD / "accs.json"; CF = DD / "codes.json"
LK = threading.Lock()
HDR = {"User-Agent": "Mozilla/5.0 (Linux; Android 13)", "Origin": "https://web.telegram.org",
       "Referer": "https://web.telegram.org/", "Content-Type": "application/json",
       "Accept": "application/json, */*"}
BANNER = ("A1ZTUS BYPASS\n"
          "v4.0 · bot edition\n"
          "-------------------------")
PHOTO = "https://i.ibb.co/FqJY2BpV/Photoroom-20260907-183658676-2.png"

def lj(p, d):
    if p.exists():
        try: return json.loads(p.read_text())
        except: pass
    return d

def sj(p, d):
    with LK: p.write_text(json.dumps(d, indent=2, ensure_ascii=False))

A = lj(AF, {}); UC = set(lj(CF, []))
PEND = {}; PWD = {}
WORKERS = {}; STOP = {}
WATCH = None

def ok(u): return not ALLOWED or u in ALLOWED

def fx(x, p=2):
    try: return f"{float(x):,.{p}f}"
    except: return str(x)

def api(name, ep, x=None, t=12):
    a = A.get(name)
    if not a: return None
    idata = a.get("init_data")
    if not idata: return None
    b = {"initData": idata}
    if x: b.update(x)
    try:
        return requests.post(BASE + ep, headers=HDR, json=b, timeout=t)
    except Exception as e:
        print(f"[api {name}] {e}")
        return None

async def fetch_id(sess):
    c = TelegramClient(StringSession(sess), API_ID, API_HASH)
    await c.connect()
    try:
        if not await c.is_user_authorized(): return None
        bot = await c.get_entity(BOT_USER)
        for pl in ("android", "web", "ios"):
            try:
                res = await c(functions.messages.RequestWebViewRequest(peer=bot, bot=bot, platform=pl,
                    url=BASE + "/", from_bot_menu=False))
                u = res.url
                if "#tgWebAppData=" in u:
                    fr = u.split("#tgWebAppData=", 1)[1]
                    raw = re.split(r"&tgWebAppVersion|&tgWebAppPlatform|&tgWebAppThemeParams", fr)[0]
                    return urllib.parse.unquote(raw)
                if "tgWebAppData=" in u:
                    fr = u.split("tgWebAppData=", 1)[1]
                    return urllib.parse.unquote(fr.split("&")[0])
            except: pass
        return None
    finally:
        try: await c.disconnect()
        except: pass

async def refresh(name):
    a = A.get(name)
    if not a: return False
    try:
        f = await fetch_id(a["session_string"])
        if f:
            a["init_data"] = f; a["init_ts"] = time.time()
            sj(AF, A)
            return True
    except Exception as e:
        print(f"[refresh {name}] {e}")
    return False

def parse_wait(m):
    if not m: return 30
    x = re.search(r"(\d+)\s*ph[uú]t", m)
    if x: return int(x.group(1)) * 60 + 5
    x = re.search(r"(\d+)\s*gi[aâ]y", m)
    if x: return int(x.group(1)) + 2
    if "quá nhanh" in m or "quá nhiều" in m: return 30
    return 60

async def task(name, tk, ep, b=None, ck=None, cs=0):
    a = A.get(name)
    if not a: return None
    cd = a.setdefault("cd", {})
    now = time.time()
    if ck and cd.get(ck, 0) > now: return None
    r = await asyncio.to_thread(api, name, ep, b)
    if not r: return None
    try: j = r.json()
    except: return None
    if j.get("success"):
        st = a.setdefault("stats", {}); st[tk] = st.get(tk, 0) + 1
        if cs: cd[ck or tk] = now + cs
        sj(AF, A)
        return j
    m = j.get("error") or j.get("message") or ""
    if m: cd[ck or tk] = now + parse_wait(m)
    return None

async def farm_loop(name, app):
    ev = STOP[name]
    if not A[name].get("init_data"): await refresh(name)
    while not ev.is_set():
        try:
            a = A.get(name)
            if not a: break
            if time.time() - a.get("init_ts", 0) > TTL: await refresh(name)
            r = await asyncio.to_thread(api, name, "/api/login")
            if not r or r.status_code != 200:
                await asyncio.sleep(30); continue
            try: u = r.json().get("user", {}); a["user"] = u
            except: u = a.get("user", {})
            oil = u.get("oil_balance", 0); f = a.get("flags", {})
            if f.get("mine") and not u.get("is_mining"):
                await task(name, "mine", "/api/start-mine", ck="mine", cs=30)
            if f.get("claim"): await task(name, "claim", "/api/claim", ck="claim", cs=45)
            if f.get("watch"): await task(name, "watch", "/api/watch-video", ck="watch", cs=15 * 60 + 10)
            if f.get("box") and u.get("mystery_boxes", 0) > 0:
                await task(name, "box", "/api/open-box-all", ck="box", cs=5)
            if f.get("craft") and u.get("shards", 0) >= 10 and u.get("tickets", 0) < 50:
                await task(name, "craft", "/api/craft-ticket", ck="craft", cs=3)
            if f.get("spin") and u.get("tickets", 0) > 0:
                await task(name, "spin", "/api/spin", ck="spin", cs=4)
            if f.get("exchange") and oil >= MIN_EX:
                await task(name, "exchange", "/api/exchange", b={"oilAmount": MIN_EX}, ck="exchange", cs=10)
            if f.get("upgrade") and oil >= 50000:
                for t in ("speed", "capacity"):
                    j = await task(name, "upgrade", "/api/upgrade", b={"type": t}, ck=f"upg_{t}", cs=15)
                    if j: break
            await asyncio.sleep(20)
        except asyncio.CancelledError: break
        except Exception as e:
            print(f"[farm {name}] {e}")
            await asyncio.sleep(20)
    WORKERS.pop(name, None)

def start_farm(app, name):
    if name in WORKERS and not WORKERS[name].done(): return False
    ev = threading.Event(); STOP[name] = ev
    WORKERS[name] = asyncio.create_task(farm_loop(name, app)); return True

def stop_farm(name):
    ev = STOP.get(name)
    if ev: ev.set()
    t = WORKERS.get(name)
    if t and not t.done(): t.cancel()

async def watcher_loop(app):
    if not A: return
    fn = next((n for n, a in A.items() if a.get("session_string")), None)
    if not fn: return
    c = TelegramClient(StringSession(A[fn]["session_string"]), API_ID, API_HASH)
    await c.connect()
    if not await c.is_user_authorized():
        await c.disconnect(); return
    try: ent = await c.get_entity(CHANNEL)
    except Exception as e:
        print(f"[watcher] {e}"); await c.disconnect(); return
    @c.on(events.NewMessage(chats=ent))
    async def h(ev):
        t = ev.message.message or ""
        for code in re.findall(r"VUADAUMO_[A-Z0-9]{5,}", t.upper()):
            if code in UC: continue
            UC.add(code); sj(CF, list(UC))
            print(f"[watcher] {code}")
            for nm in list(A.keys()):
                r = await asyncio.to_thread(api, nm, "/api/redeem-code", {"code": code})
                if r and r.status_code == 200:
                    try:
                        j = r.json()
                        if j.get("success"):
                            A[nm].setdefault("stats", {})["redeem"] = A[nm]["stats"].get("redeem", 0) + 1
                            sj(AF, A)
                    except: pass
    await c.run_until_disconnected()

def kb_main():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Them Acc", callback_data="add"),
         InlineKeyboardButton("📋 Panel", callback_data="panel_list")],
        [InlineKeyboardButton("▶️ Farm All", callback_data="start_all"),
         InlineKeyboardButton("⏹ Stop All", callback_data="stop_all")],
        [InlineKeyboardButton("📊 Live", callback_data="live"),
         InlineKeyboardButton("🎁 Auto Code", callback_data="code_tog")],
        [InlineKeyboardButton("🔄 Refresh All", callback_data="rf_all"),
         InlineKeyboardButton("🗑 Xoa Acc", callback_data="del_list")],
    ])

def kb_panel(n, f, run):
    def b(k, lb):
        v = f.get(k, False); return InlineKeyboardButton(("✅ " if v else "❌ ") + lb, callback_data=f"tog:{n}:{k}")
    rb = InlineKeyboardButton("⏹ Stop", callback_data=f"stop:{n}") if run else InlineKeyboardButton("▶️ Start", callback_data=f"start:{n}")
    return InlineKeyboardMarkup([
        [b("mine", "Mine"), b("claim", "Claim"), b("watch", "Watch")],
        [b("box", "Box"), b("craft", "Craft"), b("spin", "Spin")],
        [b("exchange", "Exchange"), b("upgrade", "Upgrade")],
        [rb, InlineKeyboardButton("💰 Rut", callback_data=f"wd:{n}")],
        [InlineKeyboardButton("⬆️ Upgrade", callback_data=f"up:{n}"),
         InlineKeyboardButton("🔄 Refresh", callback_data=f"rf:{n}")],
        [InlineKeyboardButton("🔙 Back", callback_data="menu")],
    ])

def panel_text(n):
    a = A.get(n, {}); u = a.get("user", {})
    run = n in WORKERS and not WORKERS[n].done()
    st = "🟢 RUNNING" if run else "🔴 STOPPED"
    s = a.get("stats", {})
    oil = fx(u.get("oil_balance", 0))
    return (f"╔══ ACC: {n.upper()} ══╗\n"
            f"📱 {a.get('phone', '?')}\n"
            f"👤 @{u.get('username', '?')}\n"
            f"💰 oil: {oil} · vnd: {u.get('vnd_balance', 0)}\n"
            f"⚙️ spd:{u.get('speed_lvl', 0)} cap:{u.get('capacity_lvl', 0)}\n"
            f"🎒 tkt:{u.get('tickets', 0)} shd:{u.get('shards', 0)} box:{u.get('mystery_boxes', 0)}\n"
            f"📡 {st}\n"
            f"clm:{s.get('claim', 0)} vid:{s.get('watch', 0)} box:{s.get('box', 0)} spin:{s.get('spin', 0)} exch:{s.get('exchange', 0)} rdm:{s.get('redeem', 0)}")

async def cmd_start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not ok(u.effective_user.id):
        await u.message.reply_text("⛔"); return
    try:
        await u.message.reply_photo(PHOTO, caption=BANNER, reply_markup=kb_main())
    except:
        await u.message.reply_text(BANNER, reply_markup=kb_main())

async def edit(q, txt, kb):
    try: await q.edit_message_caption(caption=txt, parse_mode=ParseMode.HTML, reply_markup=kb)
    except:
        try: await q.edit_message_text(txt, parse_mode=ParseMode.HTML, reply_markup=kb)
        except: pass

async def cb_menu(u, c):
    q = u.callback_query; await q.answer(); await edit(q, BANNER, kb_main())

async def cb_panel_list(u, c):
    q = u.callback_query; await q.answer()
    if not A: await edit(q, "📭 chua co acc", kb_main()); return
    rows = [[InlineKeyboardButton(f"👤 {n}", callback_data=f"panel:{n}")] for n in A]
    rows.append([InlineKeyboardButton("🔙 Back", callback_data="menu")])
    await edit(q, "📋 CHON ACC", InlineKeyboardMarkup(rows))

async def cb_panel(u, c):
    q = u.callback_query; await q.answer()
    n = q.data.split(":", 1)[1]
    if n not in A: await q.answer("not found", show_alert=True); return
    r = await asyncio.to_thread(api, n, "/api/login")
    if r and r.status_code == 200:
        try: A[n]["user"] = r.json().get("user", {}); sj(AF, A)
        except: pass
    run = n in WORKERS and not WORKERS[n].done()
    await edit(q, panel_text(n), kb_panel(n, A[n].get("flags", {}), run))

async def cb_tog(u, c):
    q = u.callback_query
    _, n, k = q.data.split(":", 2)
    if n not in A: await q.answer("not found"); return
    f = A[n].setdefault("flags", {}); f[k] = not f.get(k, False); sj(AF, A)
    await q.answer(f"{k}→{'ON' if f[k] else 'OFF'}")
    await cb_panel(u, c)

async def cb_start_acc(u, c):
    q = u.callback_query; n = q.data.split(":", 1)[1]
    if n not in A: await q.answer("not found"); return
    okk = start_farm(c.application, n)
    await q.answer("started" if okk else "running")
    await cb_panel(u, c)

async def cb_stop_acc(u, c):
    q = u.callback_query; n = q.data.split(":", 1)[1]
    stop_farm(n); await q.answer("stopped"); await cb_panel(u, c)

async def cb_start_all(u, c):
    q = u.callback_query; cnt = 0
    for n in A:
        if start_farm(c.application, n): cnt += 1
    await q.answer(f"started {cnt}"); await cb_menu(u, c)

async def cb_stop_all(u, c):
    q = u.callback_query
    for n in list(WORKERS.keys()): stop_farm(n)
    await q.answer("stopped all"); await cb_menu(u, c)

async def cb_rf_all(u, c):
    q = u.callback_query; await q.answer("refreshing...")
    for n in A: await refresh(n)
    await q.answer("done", show_alert=True); await cb_menu(u, c)

async def cb_rf(u, c):
    q = u.callback_query; n = q.data.split(":", 1)[1]
    await q.answer("refreshing...")
    okk = await refresh(n); await q.answer("OK" if okk else "FAIL", show_alert=True)
    await cb_panel(u, c)

async def cb_wd(u, c):
    q = u.callback_query; n = q.data.split(":", 1)[1]; await q.answer()
    PWD[u.effective_user.id] = n
    a = A.get(n, {}); uu = a.get("user", {})
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data=f"panel:{n}")]])
    await edit(q, f"💰 RUT {n.upper()}\n\nVND: {uu.get('vnd_balance', 0)}\n"
                  f"Bank: {uu.get('bank_name', '?')} / {uu.get('bank_account', '?')}\n\n"
                  f"Gui so VND:", kb)

async def cb_up(u, c):
    q = u.callback_query; n = q.data.split(":", 1)[1]; await q.answer()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡ Speed", callback_data=f"upgo:{n}:speed")],
        [InlineKeyboardButton("📦 Capacity", callback_data=f"upgo:{n}:capacity")],
        [InlineKeyboardButton("🔙 Back", callback_data=f"panel:{n}")]])
    await edit(q, f"⬆️ UPGRADE {n.upper()}", kb)

async def cb_upgo(u, c):
    q = u.callback_query; _, n, t = q.data.split(":", 2); await q.answer("upgrading...")
    r = await asyncio.to_thread(api, n, "/api/upgrade", {"type": t})
    if r and r.status_code == 200:
        try:
            j = r.json()
            if j.get("success"):
                A[n]["user"] = j.get("user", {}); sj(AF, A)
                await q.answer("✔ " + str(j.get("message")), show_alert=True)
            else:
                await q.answer("✘ " + str(j.get("error") or j.get("message")), show_alert=True)
        except: pass
    await cb_panel(u, c)

async def cb_code_tog(u, c):
    global WATCH
    q = u.callback_query
    if WATCH and not WATCH.done():
        WATCH.cancel(); WATCH = None; await q.answer("OFF", show_alert=True)
    else:
        if not A:
            await q.answer("Chua co acc nao", show_alert=True)
        else:
            try:
                WATCH = asyncio.create_task(watcher_loop(c.application))
                await q.answer("ON", show_alert=True)
            except Exception as e:
                await q.answer(f"ERR: {e}", show_alert=True)

async def cb_live(u, c):
    q = u.callback_query; await q.answer()
    ls = ["📊 LIVE", ""]
    for nm, t in WORKERS.items():
        if t.done(): continue
        a = A.get(nm, {}); uu = a.get("user", {}); s = a.get("stats", {})
        oil = fx(uu.get("oil_balance", 0))
        ls.append(f"🟢 {nm}  oil:{oil}  vnd:{uu.get('vnd_balance', 0)}")
        ls.append(f"   clm:{s.get('claim', 0)} vid:{s.get('watch', 0)} box:{s.get('box', 0)} exch:{s.get('exchange', 0)}")
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Refresh", callback_data="live"),
                                 InlineKeyboardButton("🔙 Back", callback_data="menu")]])
    await edit(q, "\n".join(ls) if len(ls) > 2 else "chua chay acc nao", kb)

async def cb_del_list(u, c):
    q = u.callback_query; await q.answer()
    if not A: await q.answer("trong", show_alert=True); return
    rows = [[InlineKeyboardButton(f"🗑 {n}", callback_data=f"del:{n}")] for n in A]
    rows.append([InlineKeyboardButton("🔙 Back", callback_data="menu")])
    await edit(q, "🗑 CHON XOA", InlineKeyboardMarkup(rows))

async def cb_del(u, c):
    q = u.callback_query; n = q.data.split(":", 1)[1]
    if n in WORKERS: stop_farm(n)
    A.pop(n, None); sj(AF, A)
    await q.answer(f"xoa {n}", show_alert=True); await cb_menu(u, c)

ASK_NAME, ASK_PHONE, ASK_OTP, ASK_PWD = range(4)

async def add_start(u, c):
    q = u.callback_query; await q.answer()
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data="menu")]])
    await edit(q, "➕ THEM ACC\n\nGui ten acc (vd FOX):", kb)
    return ASK_NAME

async def add_name(u, c):
    n = u.message.text.strip()
    if not n or n in A:
        await u.message.reply_text("❌ trung/trong. Nhap lai:"); return ASK_NAME
    c.user_data["an"] = n
    await u.message.reply_text(f"📱 SDT cho {n} (+84...):")
    return ASK_PHONE

async def add_phone(u, c):
    ph = u.message.text.strip()
    if not ph.startswith("+"):
        await u.message.reply_text("❌ can +84. Nhap lai:"); return ASK_PHONE
    n = c.user_data["an"]; await u.message.reply_text("⏳ gui OTP...")
    try:
        cl = TelegramClient(StringSession(), API_ID, API_HASH); await cl.connect()
        s = await cl.send_code_request(ph)
        PEND[u.effective_user.id] = {"name": n, "phone": ph, "client": cl, "hash": s.phone_code_hash}
        await u.message.reply_text("📨 OTP gui (app hoac SMS). Nhap OTP:")
        return ASK_OTP
    except Exception as e:
        await u.message.reply_text(f"❌ {e}"); return ConversationHandler.END

async def add_otp(u, c):
    code = u.message.text.strip().replace(" ", "")
    p = PEND.get(u.effective_user.id)
    if not p: await u.message.reply_text("❌ het han"); return ConversationHandler.END
    try:
        await p["client"].sign_in(phone=p["phone"], code=code, phone_code_hash=p["hash"])
    except SessionPasswordNeededError:
        await u.message.reply_text("🔐 2FA. Nhap password:"); return ASK_PWD
    except Exception as e:
        await u.message.reply_text(f"❌ {e}\nNhap lai OTP:"); return ASK_OTP
    sess = p["client"].session.save(); me = await p["client"].get_me()
    await p["client"].disconnect()
    A[p["name"]] = {"phone": p["phone"], "session_string": sess,
        "flags": {"mine": True, "claim": True, "watch": True, "box": True, "craft": True, "spin": True, "exchange": True, "upgrade": True},
        "created": datetime.now().isoformat(), "user": {}, "stats": {}, "cd": {}}
    sj(AF, A); PEND.pop(u.effective_user.id, None)
    await u.message.reply_text("⏳ lay initData...")
    okk = await refresh(p["name"])
    await u.message.reply_text(f"✅ them {p['name']}\n@{me.username or me.first_name}  initData:{'OK' if okk else 'FAIL'}",
        reply_markup=kb_main())
    return ConversationHandler.END

async def add_pwd(u, c):
    pwd = u.message.text.strip(); p = PEND.get(u.effective_user.id)
    if not p: await u.message.reply_text("❌ het han"); return ConversationHandler.END
    try: await p["client"].sign_in(password=pwd)
    except Exception as e:
        await u.message.reply_text(f"❌ {e}\nNhap lai:"); return ASK_PWD
    sess = p["client"].session.save(); me = await p["client"].get_me()
    await p["client"].disconnect()
    A[p["name"]] = {"phone": p["phone"], "session_string": sess,
        "flags": {"mine": True, "claim": True, "watch": True, "box": True, "craft": True, "spin": True, "exchange": True, "upgrade": True},
        "created": datetime.now().isoformat(), "user": {}, "stats": {}, "cd": {}}
    sj(AF, A); PEND.pop(u.effective_user.id, None)
    await refresh(p["name"])
    await u.message.reply_text(f"✅ them {p['name']}", reply_markup=kb_main())
    return ConversationHandler.END

async def add_cancel(u, c):
    p = PEND.pop(u.effective_user.id, None)
    if p:
        try: await p["client"].disconnect()
        except: pass
    await u.message.reply_text("da huy")
    return ConversationHandler.END

async def handle_text(u, c):
    n = PWD.pop(u.effective_user.id, None)
    if not n: return
    try: amt = float(u.message.text.strip().replace(",", ""))
    except: await u.message.reply_text("❌ so khong hop le"); return
    r = await asyncio.to_thread(api, n, "/api/withdraw", {"amount": amt})
    if r and r.status_code == 200:
        try:
            j = r.json()
            await u.message.reply_text(("✅ " + str(j.get("message"))) if j.get("success") else ("❌ " + str(j.get("error") or j.get("message"))), reply_markup=kb_main())
        except: await u.message.reply_text(r.text[:200], reply_markup=kb_main())
    else: await u.message.reply_text("HTTP fail", reply_markup=kb_main())

async def post_init(app):
    # watcher chi start khi user bam nut - khong block init
    print("[+] post_init ok")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_start, pattern="^add$")],
        states={ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_name)],
                ASK_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_phone)],
                ASK_OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_otp)],
                ASK_PWD: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_pwd)]},
        fallbacks=[CommandHandler("cancel", add_cancel)], per_message=False)
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(cb_menu, pattern="^menu$"))
    app.add_handler(CallbackQueryHandler(cb_panel_list, pattern="^panel_list$"))
    app.add_handler(CallbackQueryHandler(cb_panel, pattern=r"^panel:"))
    app.add_handler(CallbackQueryHandler(cb_tog, pattern=r"^tog:"))
    app.add_handler(CallbackQueryHandler(cb_start_acc, pattern=r"^start:"))
    app.add_handler(CallbackQueryHandler(cb_stop_acc, pattern=r"^stop:"))
    app.add_handler(CallbackQueryHandler(cb_start_all, pattern="^start_all$"))
    app.add_handler(CallbackQueryHandler(cb_stop_all, pattern="^stop_all$"))
    app.add_handler(CallbackQueryHandler(cb_rf_all, pattern="^rf_all$"))
    app.add_handler(CallbackQueryHandler(cb_rf, pattern=r"^rf:"))
    app.add_handler(CallbackQueryHandler(cb_wd, pattern=r"^wd:"))
    app.add_handler(CallbackQueryHandler(cb_up, pattern=r"^up:"))
    app.add_handler(CallbackQueryHandler(cb_upgo, pattern=r"^upgo:"))
    app.add_handler(CallbackQueryHandler(cb_code_tog, pattern="^code_tog$"))
    app.add_handler(CallbackQueryHandler(cb_live, pattern="^live$"))
    app.add_handler(CallbackQueryHandler(cb_del_list, pattern="^del_list$"))
    app.add_handler(CallbackQueryHandler(cb_del, pattern=r"^del:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    PORT = int(os.environ.get("PORT", 8080))
    URL = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")
    TOKEN_PATH = BOT_TOKEN.replace(":", "_")
    if URL:
        # Render cap PORT, phai bind de health check pass
        print(f"[*] webhook mode port={PORT} url={URL}")
        app.run_webhook(
            listen="0.0.0.0", port=PORT,
            url_path=TOKEN_PATH,
            webhook_url=f"{URL}/{TOKEN_PATH}",
            drop_pending_updates=True,
            secret_token="a1ztus_" + BOT_TOKEN[-8:]
        )
    else:
        print("[*] polling mode")
        app.run_polling(drop_pending_updates=True, close_loop=False)

if __name__ == "__main__":
    main()