# -*- coding: utf-8 -*-
"""
用 Supabase 管理 API 把 supabase/seed.sql 直接套用到線上資料庫,
等同於「把整檔貼進 SQL Editor 按 Run」,免手動複製貼上。

seed.sql 為 idempotent upsert,重複執行安全。

前置:.env.local 需有 SUPABASE_ACCESS_TOKEN(個人存取權杖)與 PROJECT_REF。
用法:python scripts/apply_seed.py
僅標準庫,免裝套件。
"""
import json
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV = ROOT / ".env.local"
SEED = ROOT / "supabase" / "seed.sql"
API = "https://api.supabase.com"


def load_env():
    env = {}
    for line in ENV.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"')
    return env


def run_query(ref, token, sql):
    body = json.dumps({"query": sql}).encode("utf-8")
    r = urllib.request.Request(
        f"{API}/v1/projects/{ref}/database/query",
        data=body, method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "tw-dict-apply-seed/1.0",
        },
    )
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else []
    except urllib.error.HTTPError as e:
        raise SystemExit(f"管理 API 執行失敗 {e.code}:{e.read().decode('utf-8', 'ignore')[:400]}")


def main():
    env = load_env()
    token = env.get("SUPABASE_ACCESS_TOKEN")
    ref = env.get("PROJECT_REF")
    if not token:
        raise SystemExit("請先在 .env.local 填入 SUPABASE_ACCESS_TOKEN")
    if not ref:
        raise SystemExit("請先在 .env.local 填入 PROJECT_REF")
    if not SEED.exists():
        raise SystemExit(f"找不到 {SEED}(先跑 python scripts/gen_seed.py)")

    sql = SEED.read_text(encoding="utf-8")
    print(f"→ 套用 seed.sql 到專案 {ref}…")
    run_query(ref, token, sql)

    # 回報實際入庫筆數,確認成功
    rows = run_query(ref, token, "select count(*) as n from public.terms;")
    n = rows[0]["n"] if rows else "?"
    print(f"[完成] terms 目前共 {n} 筆。")


if __name__ == "__main__":
    main()
