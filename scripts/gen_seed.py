# -*- coding: utf-8 -*-
"""
把 dict/terms.json 轉成 supabase/seed.sql。
產出的 SQL 可重複貼進 Supabase SQL Editor 執行(idempotent upsert):
以 (tw, cn, category) 為唯一鍵,新詞會 insert、既有詞會更新 status/note,
不會產生重複列,也不會動到你自己捕捉的 pending 詞。
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
        "-- 可重複執行:以 (tw, cn, category) 為唯一鍵 upsert,整檔貼上 Run 即可\n"
        "-- 新詞會 insert、既有詞更新 status/note,不會重複,也不動你捕捉的 pending 詞\n\n"
        "-- 確保唯一鍵存在(schema.sql 已建則略過)\n"
        "create unique index if not exists terms_seed_key_idx\n"
        "  on public.terms (tw, cn, category);\n\n"
        "insert into public.terms (tw, cn, category, status, note) values\n"
        + ",\n".join(rows)
        + "\non conflict (tw, cn, category) do update set\n"
        "  status = excluded.status,\n"
        "  note   = excluded.note;\n"
    )
    OUT.write_text(sql, encoding="utf-8")
    print(f"已產出 {OUT.relative_to(ROOT)}({len(rows)} 筆)")


if __name__ == "__main__":
    main()
