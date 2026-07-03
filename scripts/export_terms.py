# -*- coding: utf-8 -*-
"""
把 Supabase 雲端詞庫匯回 dict/terms.json(只匯出 status='confirmed' 的詞,
也就是「已查證、可公開」的部分;pending/disputed 留在雲端等查證)。
之後再跑 python dict/build.py 就能更新公開用的 CSV / Markdown。

需要 .env.local 內含:
  SUPABASE_URL=https://xxxx.supabase.co
  SUPABASE_SERVICE_KEY=（service_role 金鑰,僅本機使用,已被 .gitignore 排除)

用法:python scripts/export_terms.py
僅標準庫,免裝任何套件。
"""
import json
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TERMS = ROOT / "dict" / "terms.json"


def load_env():
    env = {}
    p = ROOT / ".env.local"
    if not p.exists():
        raise SystemExit("找不到 .env.local,請先建立並填入 SUPABASE_URL 與 SUPABASE_SERVICE_KEY")
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"')
    return env


def main():
    env = load_env()
    base = env["SUPABASE_URL"].rstrip("/")
    key = env["SUPABASE_SERVICE_KEY"]
    url = f"{base}/rest/v1/terms?select=tw,cn,category,note&status=eq.confirmed&order=category,cn"
    req = urllib.request.Request(url, headers={"apikey": key, "Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            rows = json.load(resp)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Supabase 回應錯誤 {e.code}:{e.read().decode('utf-8', 'ignore')}")

    entries = [
        {
            "tw": r.get("tw") or "",
            "cn": r.get("cn") or "",
            "category": r.get("category") or "未分類",
            "note": r.get("note") or "",
        }
        for r in rows
    ]

    doc = json.load(TERMS.open(encoding="utf-8"))
    doc["entries"] = entries
    TERMS.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已從雲端匯回 {len(entries)} 筆 → {TERMS.relative_to(ROOT)}")
    print("接著可執行:python dict/build.py  以更新 CSV / Markdown")


if __name__ == "__main__":
    main()
