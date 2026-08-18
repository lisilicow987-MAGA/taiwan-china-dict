# -*- coding: utf-8 -*-
"""比對「字典 terms.json」與「守衛 mainland_scan.py」的收詞差異。

用法：python dict/check_scanner_sync.py

為什麼需要這支：同一件事被記在兩個地方，會動的那份繼續走，另一份安靜地開始
說謊，而且不會示警。這兩份的維護入口完全不同——維護字典 app 時不會想到守衛，
被守衛擋下來時就直接補在守衛裡——沒有任何日常動作會同時碰到兩份。

**比對軸是「臺灣用語」而不是「中國用語」**，這點是 2026-08-18 才釐清的：
terms.json 的 `cn` 欄記的是簡體（软件、视频），守衛的 key 記的是繁體書寫的
中國用語（軟件、視頻）。直接對撞只有簡繁同形的詞對得上，會得出「重疊只有 8 個」
這種假象；以臺灣用語為軸，真正的概念重疊是 21 個。

本工具只報告、不改檔、不擋流程（退出碼恆為 0）。
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TERMS = ROOT / "terms.json"
SCANNER = Path.home() / "OneDrive" / ".claude-sync" / "scripts" / "mainland_scan.py"

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def head(s):
    """取用語的主體：『陷阱/容易出錯的地方』→『陷阱』，『資訊（多數用資訊）』→『資訊』。"""
    return re.split(r"[（(/]", s)[0].strip()


def load_scanner():
    """從守衛原始碼抽出「中國用語 -> 臺灣用語」的對照。"""
    src = SCANNER.read_text(encoding="utf-8")
    return dict(re.findall(r'"([一-鿿/]+)"\s*:\s*"([^"]+)"', src))


def main():
    if not TERMS.exists() or not SCANNER.exists():
        print("找不到 terms.json 或 mainland_scan.py，略過比對")
        return
    terms = json.loads(TERMS.read_text(encoding="utf-8"))["entries"]
    scanner = load_scanner()

    dict_tw = {head(e["tw"]) for e in terms}
    scan_tw = {head(v) for v in scanner.values()}
    both = dict_tw & scan_tw
    only_scan = sorted(scan_tw - dict_tw)
    only_dict = sorted(dict_tw - scan_tw)

    print(f"字典收錄概念：{len(dict_tw)}　守衛收錄概念：{len(scan_tw)}")
    print(f"兩邊都有：{len(both)}")
    print(f"只在守衛、字典沒收：{len(only_scan)}")
    print(f"只在字典、守衛擋不到：{len(only_dict)}")
    print()
    if only_scan:
        print("守衛擋得到但字典沒收（補進 terms.json 就一致了）：")
        print("  " + "、".join(only_scan))
        print()
    if only_dict:
        print(f"字典有但守衛擋不到（前 30／共 {len(only_dict)}）：")
        print("  " + "、".join(only_dict[:30]))
        print()
    if not only_scan and not only_dict:
        print("✅ 差集為 0，兩份完全一致")
    else:
        print("⚠️ 兩份尚未收斂。收斂方向：terms.json 為唯一正本，守衛的字典改為生成物。")
        print("   但這不是單純聯集，有兩件事要先處理：")
        print("   1) 書寫系統不同：字典的 cn 欄記簡體，守衛要擋的是同一個詞的繁體寫法。")
        print("      簡體那一側已有簡體字表擋得住，缺的是繁體形，需要一個轉換步驟。")
        print("   2) 同字不同義：像『土豆』『窩心』在臺灣有正當且相反的意思，只能降級為")
        print("      警告，不能硬擋。字典 note 欄的 ⚠ 標記正是這類詞，可當分級的種子。")


main()
sys.exit(0)
