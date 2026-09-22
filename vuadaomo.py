#!/usr/bin/env python3
"""vuadaomo.py - A1ZTUS BYPASS bot"""
import os, sys, json, re, time, threading, asyncio, urllib.parse
from pathlib import Path
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, ContextTypes, filters)
from telethon import TelegramClient, functions, events
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
import requests
try:
    import code_feature
    HAS_CODE_FEATURE = True
except Exception as _e:
    print('[!] code_feature khong load:', _e)
    HAS_CODE_FEATURE = False

# ===== CONFIG =====
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN: sys.exit("BOT_TOKEN env missing")
try: API_ID = int(os.environ.get("API_ID", "0"))
except: sys.exit("API_ID invalid")
API_HASH = os.environ.get("API_HASH")
if not API_HASH: sys.exit("API_HASH env missing")
ADMINS = [int(x) for x in os.environ.get("ALLOWED_USERS", "").split(",") if x.strip()]
BASE = "https://vdm.builderminiapp.online"
BOT_USER = "Vua_dau_mo_bot"
CHANNELS = ["tinggg999", "chat_daumo99"]
MIN_EX = 100000
TTL = 12 * 3600
FURINA = "https://i.ibb.co/FqJY2BpV/Photoroom-20260907-183658676-2.png"
GIF_URL = os.environ.get("GIF_URL", "").strip()
DATA_DIR = Path(os.environ.get("DATA_DIR", "/tmp/vdm_bot"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
ACC_FILE = DATA_DIR / "accs.json"
CODE_FILE = DATA_DIR / "codes.json"

HEADERS = {"User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36",
    "Origin": "https://web.telegram.org", "Referer": "https://web.telegram.org/",
    "Content-Type": "application/json", "Accept": "application/json, */*"}

# ===== STORAGE =====
_lock = threading.Lock()
def _load(p, d):
    if p.exists():
        try: return json.loads(p.read_text())
        except: pass
    return d
def _save(p, v):
    with _lock: p.write_text(json.dumps(v, indent=2, ensure_ascii=False))
ACCS = _load(ACC_FILE, {})
_rc = _load(CODE_FILE, {})
if isinstance(_rc, list):
    _rc = {c: [] for c in _rc}
    _save(CODE_FILE, _rc)
REDEEMED = _rc
PEND = {}
WD_WAIT = {}
WORKERS = {}
STOP = {}
WATCH = None

# ===== UTILS =====
def is_admin(uid): return uid in ADMINS if ADMINS else False
def is_owner(uid, name):
    a = ACCS.get(name, {})
    return a.get("owner") == uid or is_admin(uid)
def user_accs(uid):
    if is_admin(uid): return list(ACCS.keys())
    return [n for n, a in ACCS.items() if a.get("owner") == uid]
def fmt(x, p=2):
    try: return "{:,.{}f}".format(float(x), p)
    except: return str(x)
def api(name, ep, extra=None, timeout=12):
    a = ACCS.get(name)
    if not a: return None
    idata = a.get("init_data")
    if not idata: return None
    body = {"initData": idata}
    if extra: body.update(extra)
    try: return requests.post(BASE + ep, headers=HEADERS, json=body, timeout=timeout)
    except Exception as e:
        print("[api " + name + "] " + str(e)); return None
def parse_wait(msg):
    if not msg: return 30
    m = re.search(r"(\d+)\s*ph[uú]t", msg)
    if m: return int(m.group(1)) * 60 + 5
    m = re.search(r"(\d+)\s*gi[aâ]y", msg)
    if m: return int(m.group(1)) + 2
    if "quá nhanh" in msg or "quá nhiều" in msg: return 30
    return 60

# ===== MTPROTO =====
async def fetch_initdata(sess_str):
    client = TelegramClient(StringSession(sess_str), API_ID, API_HASH)
    await client.connect()
    try:
        if not await client.is_user_authorized(): return None
        bot = await client.get_entity(BOT_USER)
        for platform in ("android", "web", "ios"):
            try:
                res = await client(functions.messages.RequestWebViewRequest(
                    peer=bot, bot=bot, platform=platform,
                    url=BASE + "/", from_bot_menu=False))
                url = res.url
                if "#tgWebAppData=" in url:
                    frag = url.split("#tgWebAppData=", 1)[1]
                    raw = re.split(r"&tgWebAppVersion|&tgWebAppPlatform|&tgWebAppThemeParams", frag)[0]
                    return urllib.parse.unquote(raw)
                if "tgWebAppData=" in url:
                    frag = url.split("tgWebAppData=", 1)[1]
                    return urllib.parse.unquote(frag.split("&")[0])
            except: pass
        return None
    finally:
        try: await client.disconnect()
        except: pass
async def refresh_idata(name):
    a = ACCS.get(name)
    if not a: return False
    try:
        fresh = await fetch_initdata(a["session_string"])
        if fresh:
            a["init_data"] = fresh; a["init_ts"] = time.time()
            _save(ACC_FILE, ACCS); return True
    except Exception as e: print("[refresh " + name + "] " + str(e))
    return False

# ===== FARM =====
async def do_task(name, task, ep, extra=None, cd_key=None, cd_secs=0):
    a = ACCS.get(name)
    if not a: return None
    cd = a.setdefault("cd", {})
    now = time.time()
    if cd_key and cd.get(cd_key, 0) > now: return None
    r = await asyncio.to_thread(api, name, ep, extra)
    if not r: return None
    try: j = r.json()
    except: return None
    if j.get("success"):
        st = a.setdefault("stats", {})
        st[task] = st.get(task, 0) + 1
        if cd_secs: cd[cd_key or task] = now + cd_secs
        _save(ACC_FILE, ACCS); return j
    msg = j.get("error") or j.get("message") or ""
    if msg: cd[cd_key or task] = now + parse_wait(msg)
    return None
async def farm_loop(name):
    ev = STOP[name]
    if not ACCS[name].get("init_data"): await refresh_idata(name)
    while not ev.is_set():
        try:
            a = ACCS.get(name)
            if not a: break
            if time.time() - a.get("init_ts", 0) > TTL: await refresh_idata(name)
            r = await asyncio.to_thread(api, name, "/api/login")
            if not r or r.status_code != 200:
                await asyncio.sleep(30); continue
            try: u = r.json().get("user", {}); a["user"] = u
            except: u = a.get("user", {})
            oil = u.get("oil_balance", 0)
            f = a.get("flags", {})
            if REDEEMED:
                rn = 0
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
                    rn += 1
                    if rn >= 5: break
            if HAS_CODE_FEATURE:
                try: await code_feature.try_retro(name, a)
                except: pass
            if f.get("mine") and not u.get("is_mining"):
                await do_task(name, "mine", "/api/start-mine", cd_key="mine", cd_secs=30)
            if f.get("claim"): await do_task(name, "claim", "/api/claim", cd_key="claim", cd_secs=45)
            if f.get("watch"): await do_task(name, "watch", "/api/watch-video", cd_key="watch", cd_secs=15*60+10)
            if f.get("box") and u.get("mystery_boxes", 0) > 0:
                await do_task(name, "box", "/api/open-box-all", cd_key="box", cd_secs=5)
            if f.get("craft") and u.get("shards", 0) >= 10 and u.get("tickets", 0) < 50:
                await do_task(name, "craft", "/api/craft-ticket", cd_key="craft", cd_secs=3)
            if f.get("spin") and u.get("tickets", 0) > 0:
                await do_task(name, "spin", "/api/spin", cd_key="spin", cd_secs=4)
            if f.get("exchange") and oil >= MIN_EX:
                await do_task(name, "exchange", "/api/exchange", extra={"oilAmount": MIN_EX}, cd_key="exchange", cd_secs=10)
            if f.get("upgrade") and oil >= 50000:
                for t in ("speed", "capacity"):
                    j = await do_task(name, "upgrade", "/api/upgrade", extra={"type": t}, cd_key="upg_" + t, cd_secs=15)
                    if j: break
            await asyncio.sleep(20)
        except asyncio.CancelledError: break
        except Exception as e: print("[farm " + name + "] " + str(e)); await asyncio.sleep(20)
    WORKERS.pop(name, None)
def start_farm(app, name):
    if name in WORKERS and not WORKERS[name].done(): return False
    ev = threading.Event(); STOP[name] = ev
    WORKERS[name] = asyncio.create_task(farm_loop(name)); return True
def stop_farm(name):
    ev = STOP.get(name)
    if ev: ev.set()
    t = WORKERS.get(name)
    if t and not t.done(): t.cancel()

# ===== WATCHER =====
async def watcher_loop(app):
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
    await client.run_until_disconnected()


def main_caption():
    nn = len(ACCS); on = 0
    for w in WORKERS.values():
        try:
            if not w.done(): on += 1
        except: pass
    try: wr = "BẬT" if (WATCH and not WATCH.done()) else "TẮT"
    except: wr = "TẮT"
    return ("<b>🔥 A1ZTUS BYPASS</b>\n"
        "<i>⚡ Trung tâm điều khiển Vua Dầu Mỏ</i>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "<b>📊 TỔNG QUAN</b>\n"
        "👥 Tài khoản: <b>" + str(nn) + "</b>\n"
        "▶️ Đang farm: <b>" + str(on) + "</b>\n"
        "🎁 Code đã dùng: <b>" + str(len(REDEEMED)) + "</b>\n"
        "📡 Theo dõi code: <b>" + wr + "</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "<i>💡 Chọn chức năng bên dưới</i>")
def kb_main():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕  Thêm tài khoản", callback_data="add"),
         InlineKeyboardButton("📋  Danh sách acc", callback_data="panel_list")],
        [InlineKeyboardButton("▶️  Bật tất cả", callback_data="start_all"),
         InlineKeyboardButton("⏹  Tắt tất cả", callback_data="stop_all")],
        [InlineKeyboardButton("📊  Live view", callback_data="live"),
         InlineKeyboardButton("📜  Quan ly code", callback_data="code_menu")],
        [InlineKeyboardButton("🔄  Làm mới tất cả", callback_data="rf_all"),
         InlineKeyboardButton("🗑  Xóa acc", callback_data="del_list")],
        [InlineKeyboardButton("🔗  Chia sẻ bot", callback_data="share_help"),
         InlineKeyboardButton("🆔  ID của tôi", callback_data="myid_help")],
        [InlineKeyboardButton("🔑  Thêm bằng session (khuyến nghị)", callback_data="addsess_help")],
    ])
def kb_panel(n, f, run):
    def b(k, lb):
        v = f.get(k, False)
        mark = "🟢" if v else "🔴"
        return InlineKeyboardButton(mark + " " + lb, callback_data="tog:" + n + ":" + k)
    rb = (InlineKeyboardButton("⏹  Dừng farm", callback_data="stop:" + n) if run else
          InlineKeyboardButton("▶️  Bắt đầu farm", callback_data="start:" + n))
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
    ])
def panel_text(n):
    a = ACCS.get(n, {}); u = a.get("user", {})
    try: run = n in WORKERS and not WORKERS[n].done()
    except: run = False
    st = "🟢 <b>ĐANG CHẠY</b>" if run else "🔴 <b>ĐANG DỪNG</b>"
    s = a.get("stats", {})
    return ("👤 <b>" + n.upper() + "</b>\n"
        "📱 " + str(a.get("phone", "?")) + "\n"
        "🆔 @" + str(u.get("username", "?")) + "\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "💰 Dầu: <b>" + fmt(u.get("oil_balance", 0)) + "</b>\n"
        "💵 VND: <b>" + str(u.get("vnd_balance", 0)) + "</b>\n"
        "⚡ Tốc độ: <b>" + str(u.get("speed_lvl", 0)) + "</b>   "
        "📦 Sức chứa: <b>" + str(u.get("capacity_lvl", 0)) + "</b>\n"
        "🎫 Vé: <b>" + str(u.get("tickets", 0)) + "</b>   "
        "💎 Mảnh: <b>" + str(u.get("shards", 0)) + "</b>   "
        "🎁 Hộp: <b>" + str(u.get("mystery_boxes", 0)) + "</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n" + st + "\n"
        "<i>📊 " + str(s.get("claim", 0)) + " thu · "
        + str(s.get("watch", 0)) + " video · "
        + str(s.get("box", 0)) + " hộp · "
        + str(s.get("spin", 0)) + " quay · "
        + str(s.get("exchange", 0)) + " đổi · "
        + str(s.get("redeem", 0)) + " code</i>")

# ===== HANDLERS =====
async def edit_msg(q, txt, kb):
    # chi edit, khong bao gio xoa + gui moi -> khong bi "loi"
    try:
        if q.message.photo:
            await q.edit_message_caption(caption=txt, parse_mode=ParseMode.HTML, reply_markup=kb)
            return
        if q.message.animation:
            await q.edit_message_caption(caption=txt, parse_mode=ParseMode.HTML, reply_markup=kb)
            return
        await q.edit_message_text(txt, parse_mode=ParseMode.HTML, reply_markup=kb)
    except Exception as e:
        msg = str(e)
        if "message is not modified" in msg:
            return
        # neu animation khong edit duoc caption -> gui photo moi lan dau
        if "animation" in msg.lower() or "caption" in msg.lower():
            try:
                await q.get_bot().send_photo(q.message.chat_id, FURINA, caption=txt, parse_mode=ParseMode.HTML, reply_markup=kb)
            except: pass
        # cac loi khac: im lang, khong xoa


async def addsess_start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text("➕ <b>THÊM BẰNG SESSION</b>\n\nNhập tên acc (vd: FOX):", parse_mode=ParseMode.HTML)
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
        "📋 Paste session string vào đây.\n\n"
        "⚠️ Bot sẽ <b>XÓA TIN NHẮN</b> chứa session ngay sau khi lưu.\n\n"
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
    await msg.edit_text("✅ Đã thêm <b>" + n + "</b>\n📡 initData: OK\n📱 " + ph, parse_mode=ParseMode.HTML, reply_markup=kb_main())
    return ConversationHandler.END

async def addsess_cancel(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text("Đã hủy.")
    return ConversationHandler.END



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
    await msg.edit_text("✅ Da them <b>" + name + "</b>\n📱 " + phone + "\n📡 initData: OK", parse_mode=ParseMode.HTML, reply_markup=kb_main())




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
    txt = ("<b>QUAN LY CODE</b>\n"
           "----------\n"
           "Tong code: <b>" + str(len(REDEEMED)) + "</b>\n"
           "Acc cua ban: <b>" + str(len(names)) + "</b>\n"
           "Code chua nhap het: <b>" + str(pending) + "</b>\n"
           "----------\n")
    recent = list(REDEEMED.items())[-15:]
    if recent:
        txt += "\n<b>15 code gan nhat:</b>\n"
        for code, accs in reversed(recent):
            txt += "<code>" + code + "</code> -> " + str(len(accs)) + " acc\n"
    else:
        txt += "\n<i>Chua co code nao</i>"
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
    await u.message.reply_text("\n".join(lines))


async def cmd_start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    # gui GIF rieng (neu co) - khong chua menu
    if GIF_URL:
        try: await u.message.reply_animation(GIF_URL)
        except: pass
    # menu la photo tinh - edit caption on dinh
    cap = main_caption(); kb = kb_main()
    try: await u.message.reply_photo(FURINA, caption=cap, parse_mode=ParseMode.HTML, reply_markup=kb); return
    except: pass
    await u.message.reply_text(cap, parse_mode=ParseMode.HTML, reply_markup=kb)
async def cmd_share(u: Update, c: ContextTypes.DEFAULT_TYPE):
    bi = await c.bot.get_me()
    link = "https://t.me/" + bi.username
    txt = ("🔗 <b>CHIA SẺ BOT</b>\n━━━━━━━━━━━━━━━━━━━\nGửi link này cho bạn bè:\n\n"
        "👉 " + link + "\n\n<i>Mỗi người có tài khoản riêng, dữ liệu riêng.</i>")
    await u.message.reply_text(txt, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
async def cmd_myid(u: Update, c: ContextTypes.DEFAULT_TYPE):
    uid = u.effective_user.id
    role = "ADMIN" if is_admin(uid) else "USER"
    await u.message.reply_text("🆔 ID: <code>" + str(uid) + "</code>\n👤 Vai trò: <b>" + role + "</b>", parse_mode=ParseMode.HTML)
async def cb_addsess_help(u, c):
    q = u.callback_query; await q.answer()
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Quay lại", callback_data="menu")]])
    txt = ("🔑 <b>THÊM BẰNG SESSION</b>\n━━━━━━━━━━━━━━━━━━━\n\n"
        "Cách này <b>khuyến nghị</b> vì Telegram chặn login OTP từ server nước ngoài.\n\n"
        "<b>Các bước:</b>\n"
        "1️⃣ Trên máy tính, chạy script <code>get_session.py</code>\n"
        "2️⃣ Login Telegram 1 lần (nhập SĐT + OTP)\n"
        "3️⃣ Copy chuỗi session string\n"
        "4️⃣ Gõ lệnh <code>/addsession</code> trong bot này\n"
        "5️⃣ Nhập tên → SĐT → paste session\n\n"
        "<i>Bot tự xóa tin chứa session sau khi lưu.</i>")
    await edit_msg(q, txt, kb)

async def cb_menu(u, c):
    q = u.callback_query; await q.answer(); await edit_msg(q, main_caption(), kb_main())
async def cb_share_help(u, c):
    q = u.callback_query; await q.answer()
    bi = await c.bot.get_me()
    link = "https://t.me/" + bi.username
    txt = "🔗 <b>CHIA SẺ BOT</b>\n━━━━━━━━━━━━━━━━━━━\n\n👉 " + link + "\n\n<i>Mỗi người dùng có tài khoản riêng.</i>"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Quay lại", callback_data="menu")]])
    await edit_msg(q, txt, kb)
async def cb_myid_help(u, c):
    q = u.callback_query; await q.answer()
    uid = u.effective_user.id
    role = "ADMIN" if is_admin(uid) else "USER"
    txt = "🆔 <b>ID:</b> <code>" + str(uid) + "</code>\n👤 <b>Vai trò:</b> " + role
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Quay lại", callback_data="menu")]])
    await edit_msg(q, txt, kb)
async def cb_panel_list(u, c):
    q = u.callback_query; await q.answer()
    names = user_accs(u.effective_user.id)
    if not names:
        await edit_msg(q, "📭 <b>Bạn chưa có tài khoản nào</b>\n\nNhấn ➕ Thêm tài khoản để bắt đầu", kb_main()); return
    rows = [[InlineKeyboardButton("👤 " + n, callback_data="panel:" + n)] for n in names]
    rows.append([InlineKeyboardButton("🔙 Quay lại", callback_data="menu")])
    await edit_msg(q, "📋 <b>CHỌN TÀI KHOẢN</b>\n\n<i>Chạm để vào panel điều khiển</i>", InlineKeyboardMarkup(rows))
async def cb_panel(u, c):
    q = u.callback_query; await q.answer()
    n = q.data.split(":", 1)[1]
    if n not in ACCS: await q.answer("Không tìm thấy", show_alert=True); return
    if not is_owner(u.effective_user.id, n): await q.answer("Không có quyền", show_alert=True); return
    r = await asyncio.to_thread(api, n, "/api/login")
    if r and r.status_code == 200:
        try: ACCS[n]["user"] = r.json().get("user", {}); _save(ACC_FILE, ACCS)
        except: pass
    try: run = n in WORKERS and not WORKERS[n].done()
    except: run = False
    await edit_msg(q, panel_text(n), kb_panel(n, ACCS[n].get("flags", {}), run))
async def cb_tog(u, c):
    q = u.callback_query
    _, n, k = q.data.split(":", 2)
    if n not in ACCS or not is_owner(u.effective_user.id, n):
        await q.answer("Không có quyền", show_alert=True); return
    f = ACCS[n].setdefault("flags", {})
    f[k] = not f.get(k, False); _save(ACC_FILE, ACCS)
    await q.answer(("BẬT " if f[k] else "TẮT ") + k)
    await cb_panel(u, c)
async def cb_start_acc(u, c):
    q = u.callback_query; n = q.data.split(":", 1)[1]
    if n not in ACCS or not is_owner(u.effective_user.id, n):
        await q.answer("Không có quyền", show_alert=True); return
    okk = start_farm(c.application, n)
    await q.answer("Đã bật" if okk else "Đang chạy"); await cb_panel(u, c)
async def cb_stop_acc(u, c):
    q = u.callback_query; n = q.data.split(":", 1)[1]
    if n not in ACCS or not is_owner(u.effective_user.id, n):
        await q.answer("Không có quyền", show_alert=True); return
    stop_farm(n); await q.answer("Đã dừng"); await cb_panel(u, c)
async def cb_start_all(u, c):
    q = u.callback_query; cnt = 0
    for n in user_accs(u.effective_user.id):
        if start_farm(c.application, n): cnt += 1
    await q.answer("Đã bật " + str(cnt) + " tài khoản", show_alert=True); await cb_menu(u, c)
async def cb_stop_all(u, c):
    q = u.callback_query
    for n in user_accs(u.effective_user.id): stop_farm(n)
    await q.answer("Đã tắt tất cả", show_alert=True); await cb_menu(u, c)
async def cb_rf_all(u, c):
    q = u.callback_query
    await q.answer("Đang làm mới...")
    for n in user_accs(u.effective_user.id): await refresh_idata(n)
    await q.answer("Đã làm mới", show_alert=True); await cb_menu(u, c)
async def cb_rf(u, c):
    q = u.callback_query; n = q.data.split(":", 1)[1]
    if n not in ACCS or not is_owner(u.effective_user.id, n):
        await q.answer("Không có quyền", show_alert=True); return
    await q.answer("Đang làm mới...")
    okk = await refresh_idata(n)
    await q.answer("OK" if okk else "Thất bại", show_alert=True); await cb_panel(u, c)
async def cb_wd(u, c):
    q = u.callback_query; n = q.data.split(":", 1)[1]
    if n not in ACCS or not is_owner(u.effective_user.id, n):
        await q.answer("Không có quyền", show_alert=True); return
    await q.answer()
    WD_WAIT[u.effective_user.id] = n
    a = ACCS.get(n, {}); uu = a.get("user", {})
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Hủy", callback_data="panel:" + n)]])
    txt = ("💰 <b>RÚT TIỀN — " + n.upper() + "</b>\n━━━━━━━━━━━━━━━━━━━\n"
        "💵 VND: <b>" + str(uu.get("vnd_balance", 0)) + "</b>\n"
        "🏦 Ngân hàng: " + str(uu.get("bank_name", "?")) + "\n"
        "👤 Chủ TK: " + str(uu.get("bank_holder", "?")) + "\n"
        "💳 STK: " + str(uu.get("bank_account", "?")) + "\n━━━━━━━━━━━━━━━━━━━\n"
        "<i>Gửi số VND muốn rút vào chat</i>")
    await edit_msg(q, txt, kb)
async def cb_up(u, c):
    q = u.callback_query; n = q.data.split(":", 1)[1]
    if n not in ACCS or not is_owner(u.effective_user.id, n):
        await q.answer("Không có quyền", show_alert=True); return
    await q.answer()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡  Nâng tốc độ", callback_data="upgo:" + n + ":speed")],
        [InlineKeyboardButton("📦  Nâng sức chứa", callback_data="upgo:" + n + ":capacity")],
        [InlineKeyboardButton("🔙 Quay lại", callback_data="panel:" + n)]])
    await edit_msg(q, "⬆️ <b>NÂNG CẤP — " + n.upper() + "</b>\n\n<i>Chọn loại nâng cấp</i>", kb)
async def cb_upgo(u, c):
    q = u.callback_query; _, n, t = q.data.split(":", 2)
    if n not in ACCS or not is_owner(u.effective_user.id, n):
        await q.answer("Không có quyền", show_alert=True); return
    await q.answer("Đang nâng cấp...")
    r = await asyncio.to_thread(api, n, "/api/upgrade", {"type": t})
    if r and r.status_code == 200:
        try:
            j = r.json()
            if j.get("success"):
                ACCS[n]["user"] = j.get("user", {}); _save(ACC_FILE, ACCS)
                await q.answer("✓ " + str(j.get("message")), show_alert=True)
            else: await q.answer("✗ " + str(j.get("error") or j.get("message")), show_alert=True)
        except: pass
    await cb_panel(u, c)
async def cb_code_tog(u, c):
    global WATCH
    q = u.callback_query
    if WATCH and not WATCH.done():
        WATCH.cancel(); WATCH = None; await q.answer("Đã TẮT theo dõi code", show_alert=True)
    else:
        if not ACCS: await q.answer("Chưa có tài khoản nào", show_alert=True)
        else:
            try:
                WATCH = asyncio.create_task((code_feature.watcher_loop(c.application) if HAS_CODE_FEATURE else watcher_loop(c.application)))
                await q.answer("Đã BẬT theo dõi code", show_alert=True)
            except Exception as e: await q.answer("Lỗi: " + str(e), show_alert=True)
async def cb_live(u, c):
    q = u.callback_query; await q.answer()
    lines = ["📊 <b>LIVE VIEW</b>", "━━━━━━━━━━━━━━━━━━━", ""]
    any_run = False
    for nm, task in WORKERS.items():
        try:
            if task.done(): continue
        except: continue
        any_run = True
        a = ACCS.get(nm, {}); uu = a.get("user", {}); s = a.get("stats", {})
        lines.append("🟢 <b>" + nm + "</b>")
        lines.append("   💰 " + fmt(uu.get("oil_balance", 0)) + " dầu · 💵 " + str(uu.get("vnd_balance", 0)) + " VND")
        lines.append("   📊 " + str(s.get("claim", 0)) + " thu · " + str(s.get("watch", 0)) + " video · " + str(s.get("box", 0)) + " hộp")
        lines.append("")
    if not any_run: lines.append("<i>Chưa có tài khoản nào đang farm</i>")
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Làm mới", callback_data="live"),
                                 InlineKeyboardButton("🔙 Quay lại", callback_data="menu")]])
    await edit_msg(q, "\n".join(lines), kb)
async def cb_del_list(u, c):
    q = u.callback_query; await q.answer()
    names = user_accs(u.effective_user.id)
    if not names: await q.answer("Bạn chưa có tài khoản nào", show_alert=True); return
    rows = [[InlineKeyboardButton("🗑 " + n, callback_data="del:" + n)] for n in names]
    rows.append([InlineKeyboardButton("🔙 Quay lại", callback_data="menu")])
    await edit_msg(q, "🗑 <b>CHỌN TÀI KHOẢN ĐỂ XÓA</b>", InlineKeyboardMarkup(rows))
async def cb_del(u, c):
    q = u.callback_query; n = q.data.split(":", 1)[1]
    if n not in ACCS or not is_owner(u.effective_user.id, n):
        await q.answer("Không có quyền", show_alert=True); return
    if n in WORKERS: stop_farm(n)
    ACCS.pop(n, None); _save(ACC_FILE, ACCS)
    await q.answer("Đã xóa " + n, show_alert=True); await cb_menu(u, c)

# ===== CONVERSATION =====
S_NAME, S_PHONE, S_OTP, S_PWD = range(4)
AS_NAME, AS_PHONE, AS_SESS = range(10, 13)
async def add_start(u, c):
    q = u.callback_query; await q.answer()
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Hủy", callback_data="menu")]])
    await edit_msg(q, "➕ <b>THÊM TÀI KHOẢN</b>\n\n<i>Gửi tên tài khoản (vd: FOX)</i>", kb)
    return S_NAME
async def add_name(u, c):
    n = u.message.text.strip()
    if not n or n in ACCS:
        await u.message.reply_text("❌ Tên trùng hoặc trống. Nhập lại:"); return S_NAME
    c.user_data["an"] = n
    await u.message.reply_text("📱 Nhập SĐT cho <b>" + n + "</b> (vd: +84837258569):", parse_mode=ParseMode.HTML)
    return S_PHONE
async def add_phone(u, c):
    ph = u.message.text.strip()
    if not ph.startswith("+"):
        await u.message.reply_text("❌ Cần bắt đầu bằng +84. Nhập lại:"); return S_PHONE
    n = c.user_data["an"]
    await u.message.reply_text("⏳ Đang gửi OTP...")
    try:
        cl = TelegramClient(StringSession(), API_ID, API_HASH)
        await cl.connect()
        sent = await cl.send_code_request(ph)
        PEND[u.effective_user.id] = {"name": n, "phone": ph, "client": cl, "hash": sent.phone_code_hash, "owner": u.effective_user.id}
        await u.message.reply_text("📨 OTP đã gửi (về app Telegram hoặc SMS).\n\nNhập OTP:")
        return S_OTP
    except Exception as e:
        await u.message.reply_text("❌ " + str(e)); return ConversationHandler.END
async def add_otp(u, c):
    code = u.message.text.strip().replace(" ", "")
    p = PEND.get(u.effective_user.id)
    if not p: await u.message.reply_text("❌ Hết phiên. Bấm /start để làm lại."); return ConversationHandler.END
    try: await p["client"].sign_in(phone=p["phone"], code=code, phone_code_hash=p["hash"])
    except SessionPasswordNeededError:
        await u.message.reply_text("🔐 Có 2FA. Nhập mật khẩu:"); return S_PWD
    except Exception as e:
        await u.message.reply_text("❌ " + str(e) + "\n\nNhập lại OTP:"); return S_OTP
    await _finalize_add(u, c, p); return ConversationHandler.END
async def add_pwd(u, c):
    pwd = u.message.text.strip()
    p = PEND.get(u.effective_user.id)
    if not p: await u.message.reply_text("❌ Hết phiên. Bấm /start để làm lại."); return ConversationHandler.END
    try: await p["client"].sign_in(password=pwd)
    except Exception as e:
        await u.message.reply_text("❌ " + str(e) + "\n\nNhập lại mật khẩu:"); return S_PWD
    await _finalize_add(u, c, p); return ConversationHandler.END
async def _finalize_add(u, c, p):
    try:
        sess = p["client"].session.save()
        me = await p["client"].get_me()
        await p["client"].disconnect()
    except: sess = ""; me = None
    ACCS[p["name"]] = {"phone": p["phone"], "session_string": sess, "owner": p["owner"],
        "created": datetime.now().isoformat(),
        "flags": {"mine": True, "claim": True, "watch": True, "box": True, "craft": True, "spin": True, "exchange": True, "upgrade": True},
        "user": {}, "stats": {}, "cd": {}}
    _save(ACC_FILE, ACCS)
    PEND.pop(u.effective_user.id, None)
    uname = me.username if me and me.username else (me.first_name if me else "?")
    await u.message.reply_text("⏳ Đang lấy initData...")
    okk = await refresh_idata(p["name"])
    await u.message.reply_text("✅ Đã thêm <b>" + p["name"] + "</b>\n👤 @" + str(uname) + "\n📡 initData: " + ("OK" if okk else "LỖI"),
        parse_mode=ParseMode.HTML, reply_markup=kb_main())
async def add_cancel(u, c):
    p = PEND.pop(u.effective_user.id, None)
    if p:
        try: await p["client"].disconnect()
        except: pass
    await u.message.reply_text("Đã hủy.")
    return ConversationHandler.END
async def handle_text(u, c):
    n = WD_WAIT.pop(u.effective_user.id, None)
    if not n: return
    try: amt = float(u.message.text.strip().replace(",", "").replace(".", ""))
    except: await u.message.reply_text("❌ Số không hợp lệ."); return
    r = await asyncio.to_thread(api, n, "/api/withdraw", {"amount": amt})
    if r and r.status_code == 200:
        try:
            j = r.json()
            if j.get("success"): await u.message.reply_text("✅ " + str(j.get("message")), reply_markup=kb_main())
            else: await u.message.reply_text("❌ " + str(j.get("error") or j.get("message")), reply_markup=kb_main())
        except: await u.message.reply_text(r.text[:200], reply_markup=kb_main())
    else: await u.message.reply_text("❌ Gửi lệnh thất bại.", reply_markup=kb_main())

# ===== HEALTH =====
def start_health():
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200); self.send_header("Content-Type", "text/plain; charset=utf-8"); self.end_headers()
            self.wfile.write(b"A1ZTUS BYPASS alive")
        def do_HEAD(self):
            self.send_response(200); self.end_headers()
        def log_message(self, *a): pass
    port = int(os.environ.get("PORT", 8080))
    try:
        srv = HTTPServer(("0.0.0.0", port), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        print("[+] health :" + str(port))
    except Exception as e: print("[!] health: " + str(e))

async def post_init(app): print("[+] bot ready")

# ===== MAIN =====
def main():
    start_health()
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
    if HAS_CODE_FEATURE:
        try:
            code_feature.install(app, globals())
        except Exception as _e:
            print('[!] code_feature install:', _e)
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_start, pattern="^add$")],
        states={S_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_name)],
                S_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_phone)],
                S_OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_otp)],
                S_PWD: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_pwd)]},
        fallbacks=[CommandHandler("cancel", add_cancel)])
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("share", cmd_share))
    app.add_handler(CommandHandler("myid", cmd_myid))
    app.add_handler(CommandHandler("addsession", addsess_start))
    app.add_handler(CommandHandler("addsession_auto", cmd_addsession_auto))
    conv2 = ConversationHandler(
        entry_points=[CommandHandler("addsession", addsess_start)],
        states={AS_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, addsess_name)],
                AS_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, addsess_phone)],
                AS_SESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, addsess_sess)]},
        fallbacks=[CommandHandler("cancel", addsess_cancel)])
    app.add_handler(conv)
    app.add_handler(conv2)
    app.add_handler(CallbackQueryHandler(cb_menu, pattern="^menu$"))
    app.add_handler(CallbackQueryHandler(cb_addsess_help, pattern="^addsess_help$"))
    app.add_handler(CallbackQueryHandler(cb_share_help, pattern="^share_help$"))
    app.add_handler(CallbackQueryHandler(cb_myid_help, pattern="^myid_help$"))
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
    app.add_handler(CallbackQueryHandler(cb_code_menu, pattern="^code_menu$"))
    app.add_handler(CallbackQueryHandler(cb_code_retry, pattern="^code_retry$"))
    app.add_handler(CallbackQueryHandler(cb_code_export, pattern="^code_export$"))
    app.add_handler(CommandHandler("codes", cmd_codes))
    app.add_handler(CallbackQueryHandler(cb_live, pattern="^live$"))
    app.add_handler(CallbackQueryHandler(cb_del_list, pattern="^del_list$"))
    app.add_handler(CallbackQueryHandler(cb_del, pattern=r"^del:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("[*] polling...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()