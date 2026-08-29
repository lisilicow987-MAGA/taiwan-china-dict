# -*- coding: utf-8 -*-
"""
把 dict/terms.json 的策劃資料套用到線上 Supabase。

兩條路,優先用第一條:
  1. REST + service_role 金鑰(預設)。金鑰長效不過期,是日常該走的路。
  2. 管理 API + 個人存取權杖(備援)。sbp_ 權杖是短效的,會反覆失效;
     而且專案被暫停時管理 API 會回 401,看起來像憑證過期,其實是專案停了。

兩條路都是 idempotent upsert:以 (tw, cn, category) 為唯一鍵,新詞 insert、
既有詞更新 status/note。**不刪除任何列**,所以你在 app 裡隨手捕捉的 pending
詞不會被動到。

前置:.env.local 需有 SUPABASE_URL 與 SUPABASE_SERVICE_KEY(走 REST),
      或 PROJECT_REF 與 SUPABASE_ACCESS_TOKEN(走管理 API)。
用法:python scripts/apply_seed.py
僅標準庫,免裝套件。
"""
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from gen_seed import build_rows            # noqa: E402  轉換只有一份,兩條路共用

ENV = ROOT / ".env.local"
TERMS = ROOT / "dict" / "terms.json"
SEED = ROOT / "supabase" / "seed.sql"
API = "https://api.supabase.com"
CHUNK = 100                                # 一次送 100 列,失敗時比較好定位


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


def rest(url, key, path, method="GET", body=None, extra=None):
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "User-Agent": "tw-dict-apply-seed/2.0",
    }
    headers.update(extra or {})
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    req = urllib.request.Request(f"{url.rstrip('/')}/rest/v1/{path}",
                                 data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read().decode("utf-8")
        return resp.headers, (json.loads(raw) if raw.strip() else None)


def count_rows(url, key):
    """回傳線上目前的列數(用 Content-Range 讀,不必把整張表拉下來)。"""
    headers, _ = rest(url, key, "terms?select=id&limit=1",
                      extra={"Prefer": "count=exact"})
    rng = headers.get("Content-Range") or ""
    return rng.split("/")[-1] if "/" in rng else "?"


def apply_via_rest(url, key, rows):
    before = count_rows(url, key)
    print(f"→ 走 REST + service_role,線上現有 {before} 列")
    for i in range(0, len(rows), CHUNK):
        batch = rows[i:i + CHUNK]
        try:
            rest(url, key, "terms?on_conflict=tw,cn,category", method="POST", body=batch,
                 extra={"Prefer": "resolution=merge-duplicates,return=minimal"})
        except urllib.error.HTTPError as e:
            raise SystemExit(f"第 {i + 1}–{i + len(batch)} 列失敗 {e.code}:"
                             f"{e.read().decode('utf-8', 'ignore')[:400]}")
        print(f"   已送出 {min(i + CHUNK, len(rows))}/{len(rows)}")
    after = count_rows(url, key)
    print(f"[完成] terms 由 {before} 列變成 {after} 列(只新增/更新,未刪除任何列)")


def main():
    env = load_env()
    if not TERMS.exists():
        raise SystemExit(f"找不到 {TERMS}")
    rows = build_rows(json.loads(TERMS.read_text(encoding="utf-8")))
    print(f"本機的策劃資料 {len(rows)} 列")

    url, key = env.get("SUPABASE_URL"), env.get("SUPABASE_SERVICE_KEY")
    if url and key:
        apply_via_rest(url, key, rows)
        return

    # 備援:管理 API。走到這裡通常是 .env.local 還沒填 service_role 金鑰。
    print("⚠️ 找不到 SUPABASE_URL / SUPABASE_SERVICE_KEY,改走管理 API(短效權杖,易失效)")
    token, ref = env.get("SUPABASE_ACCESS_TOKEN"), env.get("PROJECT_REF")
    if not token or not ref:
        raise SystemExit("請在 .env.local 填入 SUPABASE_URL + SUPABASE_SERVICE_KEY,"
                         "或 PROJECT_REF + SUPABASE_ACCESS_TOKEN")
    if not SEED.exists():
        raise SystemExit(f"找不到 {SEED}(先跑 python scripts/gen_seed.py)")
    print(f"→ 套用 seed.sql 到專案 {ref}…")
    run_query(ref, token, SEED.read_text(encoding="utf-8"))
    got = run_query(ref, token, "select count(*) as n from public.terms;")
    print(f"[完成] terms 目前共 {got[0]['n'] if got else '?'} 筆。")


if __name__ == "__main__":
    main()
