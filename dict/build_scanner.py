# -*- coding: utf-8 -*-
"""從 terms.json 生成守衛用的字典，供 mainland_scan.py 讀取。

用法：python dict/build_scanner.py

為什麼要有這支：同一份用語清單原本存在三個地方（這份字典、守衛的原始碼、
SHARED_RULES 的錨點行），三邊各自維護、沒有任何日常動作會同時碰到兩份，
於是會動的那份繼續走，另外兩份安靜地開始說謊。改成單向生成之後，
補詞只有一個入口：terms.json。

哪些條目會被執法，由條目自己的 scan 欄決定：
    scan = "hard"     一定是中國用語 → 守衛擋下
    scan = "context"  看語境，臺灣也可能用 → 只警告
    沒有 scan 欄       只是對照字典的收錄，不執法

兩個欄位的用途：
    cn_tw    繁體書寫的中國用語，也就是守衛實際要比對的字串。
             字典的 cn 欄記簡體，但在臺灣人寫的文章裡，風險是有人用繁體
             寫出中國詞（簡體那一側另有簡體字表擋著）。省略時由 cn 轉出。
    scan_tw  守衛要顯示的建議用語。與 tw 欄不同時才需要填——字典的 tw 是
             一般語境的對照，守衛的建議常帶語境限定（例如某詞在 git 語境
             該用原文、在別處則另有譯法）。
"""
import json
import sys
from datetime import datetime
from pathlib import Path

try:
    import opencc
except ImportError:
    opencc = None

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "terms.json"
OUT = Path.home() / "OneDrive" / ".claude-sync" / "scripts" / "mainland_terms.json"

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def main():
    data = json.loads(SRC.read_text(encoding="utf-8"))
    conv = opencc.OpenCC("s2t") if opencc else None
    hard, context, missing = {}, {}, []
    exempt = []

    for e in data["entries"]:
        level = e.get("scan")
        if level not in ("hard", "context"):
            continue
        key = e.get("cn_tw")
        if not key:
            if conv is None:
                missing.append(e["cn"])
                continue
            key = conv.convert(e["cn"].split("/")[0].strip())
        (hard if level == "hard" else context)[key] = e.get("scan_tw") or e["tw"]
        # scan_not：這些片語裡雖然出現了該詞的字面，但句子本身是正確的臺灣中文,
        # 純粹是相鄰兩個詞夾出來的子字串巧合。守衛比對前會把整段片語遮掉。
        for phrase in e.get("scan_not") or []:
            if phrase not in exempt:
                exempt.append(phrase)

    if missing:
        print("缺少 cn_tw 且環境沒有 opencc,無法轉出繁體形：", "、".join(missing),
              file=sys.stderr)
        sys.exit(1)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "_generated": "由 China Shit/dict/build_scanner.py 從 terms.json 生成,請勿手動編輯",
        "_source": "dict/terms.json",
        "_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "hard": hard, "context": context, "exempt": exempt,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已產出 {OUT.name}:hard {len(hard)} 條、context {len(context)} 條、"
          f"豁免片語 {len(exempt)} 條")


if __name__ == "__main__":
    main()
