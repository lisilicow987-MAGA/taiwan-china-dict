# -*- coding: utf-8 -*-
"""
把 dict/terms.json 轉成 supabase/seed.sql。
產出的 SQL 貼進 Supabase SQL Editor 執行一次,即可把現有詞庫匯入。
既有策劃資料一律標為 status='confirmed'。
用法:python scripts/gen_seed.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "dict" / "terms.json"
OUT = ROOT / "supabase" / "seed.sql"


def q(s):
    """轉成 SQL 字串字面值;空字串/None 轉 NULL。"""
    if s is None or str(s).strip() == "":
        return "NULL"
    return "'" + str(s).replace("'", "''") + "'"


def main():
    data = json.load(SRC.open(encoding="utf-8"))
    rows = []
    for e in data["entries"]:
        rows.append(
            "  ({tw}, {cn}, {cat}, 'confirmed', {note})".format(
                tw=q(e.get("tw")),
                cn=q(e.get("cn")),
                cat=q(e.get("category") or "未分類"),
                note=q(e.get("note")),
            )
        )
    sql = (
        "-- 由 dict/terms.json 自動產生(python scripts/gen_seed.py)\n"
        "-- 貼進 Supabase SQL Editor 執行一次即可匯入現有詞庫\n\n"
        "insert into public.terms (tw, cn, category, status, note) values\n"
        + ",\n".join(rows)
        + ";\n"
    )
    OUT.write_text(sql, encoding="utf-8")
    print(f"已產出 {OUT.relative_to(ROOT)}({len(rows)} 筆)")


if __name__ == "__main__":
    main()
