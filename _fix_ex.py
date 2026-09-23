import ast, re
from pathlib import Path
p = Path.home() / "Desktop" / "vuadaomo" / "vuadaomo.py"
src = p.read_text(encoding="utf-8")

# Xoa FOX/A1ztus khoi example
old = '''"<code>FOX\\n+84837258569\\n1BVtsOIcBu7ViVQ...</code>\\n\\n"
           "<code>A1ztus\\n+84911404475\\n1BVtsOIcBu5f...</code>"'''
new = '''"<code>ACC1\\n+84999999999\\n1BVtsOIcBu7ViVQ...</code>\\n\\n"
           "<code>ACC2\\n+84988888888\\n1BVtsOIcBu5f...</code>"'''
if old in src:
    src = src.replace(old, new)
    print("[+] da sua example 1")
else:
    # Thu cach khac - doi truc tiep
    src = src.replace("FOX\\n+84837258569", "ACC1\\n+84999999999")
    src = src.replace("A1ztus\\n+84911404475", "ACC2\\n+84988888888")
    print("[+] da sua example 2 (truc tiep)")

p.write_text(src, encoding="utf-8")
ast.parse(src)
print("SYNTAX_OK")