import ast, re
from pathlib import Path

src = Path("vuadaomo.py").read_text(encoding="utf-8")
tree = ast.parse(src)

# Tập hợp tất cả các hàm được định nghĩa
defined = set()
for node in ast.walk(tree):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        defined.add(node.name)

# Tìm các handler được đăng ký trong app.add_handler
missing = []
for m in re.finditer(r'app\.add_handler\(\s*(\w+)\s*\(([^)]*)\)', src):
    handler_type = m.group(1)
    args = m.group(2)
    # Lấy tên hàm callback (tham số đầu tiên)
    cb_match = re.match(r'\s*(\w+)', args)
    if cb_match:
        cb_name = cb_match.group(1)
        if cb_name not in defined and cb_name not in ('filters', 'Update', 'TypeHandler', 'CommandHandler', 'CallbackQueryHandler', 'MessageHandler'):
            missing.append((handler_type, cb_name))

if missing:
    print("[!] CÁC HANDLER THIẾU ĐỊNH NGHĨA:")
    for ht, name in missing:
        print(f"  - {ht}: {name}")
else:
    print("[+] Tất cả handler đều đã được định nghĩa.")