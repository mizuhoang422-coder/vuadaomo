import ast
from pathlib import Path
p = Path.home() / "Desktop" / "vuadaomo" / "vuadaomo.py"
src = p.read_text(encoding="utf-8")

old = '"\\U0001f381 H\\u1ed9p: <b>" + str(u.get("mystery_boxes", 0)) + "</b>\\n"\n        err_line +'
new = '"\\U0001f381 H\\u1ed9p: <b>" + str(u.get("mystery_boxes", 0)) + "</b>\\n" +\n        err_line +'

if old in src:
    src = src.replace(old, new, 1)
    print("[+] da them dau + o cuoi dong box")
else:
    # Thu cach khac - tim dong "err_line +" dau tien
    if "err_line +\n" in src:
        src = src.replace('"</b>\\n"\n        err_line +',
                          '"</b>\\n" +\n        err_line +', 1)
        print("[+] da sua bang cach khac")
    else:
        print("[!] khong tim thay pattern")

p.write_text(src, encoding="utf-8")
ast.parse(src)
print("SYNTAX_OK")