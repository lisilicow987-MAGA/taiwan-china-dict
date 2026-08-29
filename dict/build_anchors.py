# -*- coding: utf-8 -*-
"""從 terms.json 生成 SHARED_RULES.md 的「高頻錨點」那一行。（allow-terms:file
—— 本檔會舉例說明哪些詞該改,是引用不是使用,整份不掃）

用法:python dict/build_anchors.py

為什麼要生成:那一行是同一份用語清單的第三份副本。字典改了、守衛跟著改了,
但那行是手寫的,只能靠人記得同步——2026-08-29 一天之內就手動同步了兩次,
每一次都是下一次忘記的預演。

錨點與執法是兩件事,刻意分開:
  anchor  這個詞值不值得寫進規則裡提醒(給人讀的)
  scan    這個詞要不要被守衛攔截(給機器用的)
兩者不必相同。例如「滑」的抽象義該提醒,但它是單字,滑鼠/滑動/滑倒都含它,
放進守衛只會天天誤擋——所以它有 anchor 沒有 scan。

寫入位置以標記界定,標記以外的內容一字不動:
  <!-- anchors:start ... -->
  <!-- anchors:end -->
"""
import json
import sys
from pathlib import Path

try:
    import opencc
except ImportError:
    opencc = None

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "terms.json"
TARGETS = [Path.home() / ".claude" / "SHARED_RULES.md",
           Path.home() / "OneDrive" / ".claude-sync" / "SHARED_RULES.md"]
START = "<!-- anchors:start"
END = "<!-- anchors:end -->"

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def build_line(entries):
    """相同建議用語的詞併成一組,維持原本『坑/踩坑/踩雷→陷阱』那種寫法。

    key 的 fallback 必須經過簡→繁轉換,不能直接用 cn 欄:cn 記的是簡體,而錨點行
    要提醒的是「別在繁體文章裡寫這個詞」,印簡體等於提醒錯對象。原本只有一個詞
    會走到 fallback,而它剛好簡繁同形所以完全看不出錯——這種蒙對的 bug 最難發現。
    """
    conv = opencc.OpenCC("s2t") if opencc else None
    groups = {}
    for e in entries:
        if not e.get("anchor"):
            continue
        key = e.get("cn_tw")
        if not key:
            raw = e["cn"].split("/")[0].strip()
            key = conv.convert(raw) if conv else raw
        hint = e.get("scan_tw") or e["tw"]
        groups.setdefault(hint, []).append(key)
    parts = ["/".join(ks) + "→" + hint for hint, ks in groups.items()]
    return "  - 高頻錨點（❌→✅）：" + "、".join(parts)


def main():
    entries = json.loads(SRC.read_text(encoding="utf-8"))["entries"]
    line = build_line(entries)
    n = sum(1 for e in entries if e.get("anchor"))
    written = 0
    for p in TARGETS:
        if not p.exists():
            continue                      # CI 沒有這些檔,跳過即可
        lines = p.read_text(encoding="utf-8").splitlines()
        try:
            i = next(j for j, l in enumerate(lines) if START in l)
            k = next(j for j in range(i + 1, len(lines)) if END in lines[j])
        except StopIteration:
            print(f"  ⚠️ {p} 找不到 anchors 標記,略過(請先加上標記)", file=sys.stderr)
            continue
        if lines[i + 1:k] == [line]:
            continue                      # 已是最新,不動檔案的修改時間
        lines[i + 1:k] = [line]
        p.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        written += 1
    print(f"已產出高頻錨點({n} 個詞,更新 {written} 份 SHARED_RULES)")


if __name__ == "__main__":
    main()
