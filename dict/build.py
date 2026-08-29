# -*- coding: utf-8 -*-
"""
建置腳本:以 terms.json 為唯一資料來源,產出 CSV 與 Markdown。
用法:python dict/build.py
"""
import csv
import json
import sys
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "terms.json"
CSV_OUT = ROOT / "dict.csv"
MD_OUT = ROOT / "dict.md"


def load():
    with SRC.open(encoding="utf-8") as f:
        return json.load(f)


def build_csv(data):
    entries = data["entries"]
    with CSV_OUT.open("w", encoding="utf-8-sig", newline="") as f:
        # lineterminator 寫死:csv 預設用 CRLF,而 Python 在 Windows 又會再把
        # 換行依平台轉換。兩者相乘的結果是同一份 terms.json 在 Windows 與 Linux
        # 產出的檔案每一行都不同——CI 重建後會判定「整份不同步」,但那不是真的
        # 不同步。搭配 .gitattributes 的 eol=lf,兩邊才會一致。
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["臺灣慣用語", "中國慣用語", "分類", "備註"])
        for e in entries:
            writer.writerow([e["tw"], e["cn"], e["category"], e.get("note", "")])
    return len(entries)


def build_md(data):
    meta = data["meta"]
    entries = data["entries"]

    # 依分類分組,維持出現順序
    groups = OrderedDict()
    for e in entries:
        groups.setdefault(e["category"], []).append(e)

    lines = []
    lines.append(f"# {meta['title']}\n")
    lines.append(f"> {meta['description']}\n")
    lines.append(f"- 版本:`{meta['version']}`")
    lines.append(f"- 收錄詞條:**{len(entries)}** 筆,共 **{len(groups)}** 個分類")
    lines.append(f"- 說明:{meta['generated_note']}\n")
    lines.append("> ⚠ 標記者為「同字不同義」或不完全對等的陷阱詞,使用時請特別留意。\n")

    # 目錄
    lines.append("## 目錄\n")
    for cat in groups:
        anchor = cat.replace(" ", "-")
        lines.append(f"- [{cat}](#{anchor})({len(groups[cat])})")
    lines.append("")

    for cat, items in groups.items():
        lines.append(f"## {cat}\n")
        lines.append("| 臺灣慣用語 | 中國慣用語 | 備註 |")
        lines.append("|------------|------------|------|")
        for e in items:
            note = e.get("note", "").replace("|", "\\|")
            lines.append(f"| {e['tw']} | {e['cn']} | {note} |")
        lines.append("")

    MD_OUT.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return len(entries)


def build_others():
    """順帶重建其他所有從 terms.json 衍生的檔案。

    為什麼要綁在一起:2026-08-29 發現 supabase/seed.sql 落後了 54 筆——
    8/18 補詞時只重建了 CSV/Markdown 與守衛詞表,沒有人想到還有 seed。
    衍生物只要有一個需要「另外記得跑」,它遲早會落後,而且沒有人會發現。
    這裡失敗只提示、不中斷,CSV/Markdown 已經產好了不該一起賠掉。
    """
    import subprocess
    for desc, script in (("Supabase seed", ROOT.parent / "scripts" / "gen_seed.py"),
                         ("守衛詞表", ROOT / "build_scanner.py")):
        if not script.exists():
            continue
        r = subprocess.run([sys.executable, str(script)], capture_output=True,
                           encoding="utf-8", errors="replace")
        out = (r.stdout or r.stderr or "").strip().splitlines()
        if r.returncode == 0:
            print("  " + (out[-1] if out else f"已產出{desc}"))
        else:
            print(f"  ⚠️ {desc}重建失敗:{out[-1] if out else r.returncode}", file=sys.stderr)


def main():
    if not SRC.exists():
        print(f"找不到資料來源:{SRC}", file=sys.stderr)
        sys.exit(1)
    data = load()
    n_csv = build_csv(data)
    n_md = build_md(data)
    print(f"已產出 CSV:{CSV_OUT.name}({n_csv} 筆)")
    print(f"已產出 Markdown:{MD_OUT.name}({n_md} 筆)")
    build_others()


if __name__ == "__main__":
    main()
