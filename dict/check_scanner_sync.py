# -*- coding: utf-8 -*-
"""檢查守衛用的詞表是否跟得上 terms.json。

用法：python dict/check_scanner_sync.py

原本這支是比對「字典」與「守衛原始碼裡的人工詞表」兩份清單的差集。
2026-08-18 收斂成單向生成之後，那個差集在設計上恆為 0，真正會出事的是
另一件事：**有人改了 terms.json 卻忘了跑 build_scanner.py**，於是守衛
繼續用舊詞表，而畫面上一切正常。

所以現在檢查兩件事：
  1) 生成物與 terms.json 是否同步（不同步 → 新補的詞根本沒在擋）
  2) 字典裡有多少條目已納入執法、多少條還沒決定

只報告、不改檔、不擋流程（退出碼恆為 0）。
"""
import json
import sys
from pathlib import Path

try:
    import opencc
except ImportError:
    opencc = None

ROOT = Path(__file__).resolve().parent
TERMS = ROOT / "terms.json"
BUILT = Path.home() / "OneDrive" / ".claude-sync" / "scripts" / "mainland_terms.json"

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def expected(entries):
    """算出「照現在的 terms.json 該產出什麼」，用來跟實際產出的比。"""
    conv = opencc.OpenCC("s2t") if opencc else None
    hard, ctx = {}, {}
    for e in entries:
        lvl = e.get("scan")
        if lvl not in ("hard", "context"):
            continue
        key = e.get("cn_tw")
        if not key:
            if conv is None:
                continue
            key = conv.convert(e["cn"].split("/")[0].strip())
        (hard if lvl == "hard" else ctx)[key] = e.get("scan_tw") or e["tw"]
    return hard, ctx


def main():
    if not TERMS.exists():
        print("找不到 terms.json")
        return
    entries = json.loads(TERMS.read_text(encoding="utf-8"))["entries"]
    n_hard = sum(1 for e in entries if e.get("scan") == "hard")
    n_ctx = sum(1 for e in entries if e.get("scan") == "context")
    print(f"字典條目：{len(entries)}")
    print(f"  執法（hard，直接擋）：{n_hard}")
    print(f"  執法（context,只警告）：{n_ctx}")
    print(f"  未納入執法：{len(entries) - n_hard - n_ctx}")
    print()

    if not BUILT.exists():
        print("⚠️ 找不到生成的詞表,守衛目前形同未檢查。")
        print("   修法：python dict/build_scanner.py")
        return
    built = json.loads(BUILT.read_text(encoding="utf-8"))
    if opencc is None:
        print("（未安裝 opencc,略過同步比對）")
        return
    eh, ec = expected(entries)
    drift = []
    for name, want, got in (("hard", eh, built.get("hard", {})),
                            ("context", ec, built.get("context", {}))):
        for k in sorted(set(want) | set(got)):
            if k not in got:
                drift.append(f"{name}:{k} 字典有、詞表沒有")
            elif k not in want:
                drift.append(f"{name}:{k} 詞表有、字典已移除")
            elif want[k] != got[k]:
                drift.append(f"{name}:{k} 建議用語不同")
    if not drift:
        print(f"✅ 詞表與字典同步（產出於 {built.get('_at', '?')}）")
    else:
        print(f"⚠️ 詞表落後字典 {len(drift)} 處 —— 新補的詞現在沒有在擋：")
        for x in drift[:20]:
            print("   " + x)
        print("   修法：python dict/build_scanner.py")


main()
sys.exit(0)
