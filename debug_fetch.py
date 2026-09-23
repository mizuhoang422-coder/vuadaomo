import asyncio, re, urllib.parse
from telethon import TelegramClient, functions
from telethon.sessions import StringSession

API_ID = 39640140
API_HASH = "d3550a705da8fc2982dafb5cbdc7f754"
BASE = "https://vdm.builderminiapp.online"
BOT_USER = "Vua_dau_mo_bot"

SESS = "1BVtsOIcBu7ViVQ5BLPvVOFaILHfkWyScKtjbc-NoNQczQfBel5g_hBFUZERD6o_QgKZny-m1VWTppESH7XsILIf4t0dmoyKtgUCK-XVPzlJo_PKkdmAMFMB1_O3qEN5KDZGMif-CJZUoOjZcnTX_kNCrTLEzMgoBfdEhXhwB0vn6zpWT8SGjgAV0f1fg-M-v-sXTw8cSxQaKSI4Px9LmDqHXXNQKnH_oUoieR2xLpXGcom8At1mhIms5fZ2XotV-zu9T0IYT9ntpgLXxD9dHxMWldfzxqxYGJCQBTiMdRXe6pBcyJEPPua1nvPL1iwXkDePyRO-WRyos4Ulg3aWDc1iC9rLWMvw="

async def main():
    c = TelegramClient(StringSession(SESS), API_ID, API_HASH)
    await c.connect()
    print("[*] connected:", await c.is_user_authorized())
    bot = await c.get_entity(BOT_USER)
    print("[*] bot:", bot.username, bot.id)
    for pl in ("android", "web", "ios"):
        try:
            res = await c(functions.messages.RequestWebViewRequest(
                peer=bot, bot=bot, platform=pl,
                url=BASE + "/", from_bot_menu=False))
            url = res.url
            print("[+] platform", pl, "URL len:", len(url))
            if "#tgWebAppData=" in url:
                fr = url.split("#tgWebAppData=", 1)[1]
                raw = re.split(r"&tgWebAppVersion|&tgWebAppPlatform|&tgWebAppThemeParams", fr)[0]
                initdata = urllib.parse.unquote(raw)
                print("[+] initdata len:", len(initdata))
                q = dict(urllib.parse.parse_qsl(initdata))
                print("[+] fields:", list(q.keys()))
                import json
                print("[+] user:", q.get("user", "?")[:300])
                break
            else:
                print("[-] khong co tgWebAppData")
        except Exception as e:
            print("[-]", pl, ":", e)
    await c.disconnect()

asyncio.run(main())