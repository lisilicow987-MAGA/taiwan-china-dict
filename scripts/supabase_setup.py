# -*- coding: utf-8 -*-
"""
用 Supabase 管理 API 自動完成後端接線:
  1. 抓 anon 金鑰,填進 app/config.js
  2. 設定登入白名單(Site URL / Redirect URLs)
  3. 抓 service_role 金鑰,寫回 .env.local(供 export_terms.py 用)

前置:.env.local 需有 SUPABASE_ACCESS_TOKEN(個人存取權杖)與 PROJECT_REF。
用法:python scripts/supabase_setup.py
僅標準庫,免裝套件。
"""
import json
import re
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV = ROOT / ".env.local"
CONFIG = ROOT / "app" / "config.js"
API = "https://api.supabase.com"
SITE = "http://127.0.0.1:5173"
REDIRECTS = "http://127.0.0.1:5173,http://localhost:5173"


def load_env():
    env = {}
    for line in ENV.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"')
    return env


def req(method, path, token, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    r = urllib.request.Request(
        API + path, data=data, method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) tw-dict-setup/1.0",
        },
    )
    try:
        with urllib.request.urlopen(r, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        raise SystemExit(f"管理 API {method} {path} 失敗 {e.code}:{e.read().decode('utf-8', 'ignore')[:400]}")


def set_env_var(text, key, val):
    if re.search(rf"(?m)^{key}=.*$", text):
        return re.sub(rf"(?m)^{key}=.*$", f"{key}={val}", text)
    return text.rstrip() + f"\n{key}={val}\n"


def find_key(keys, name):
    for k in keys:
        if k.get("name") == name and k.get("api_key"):
            return k["api_key"]
    return None


def main():
    env = load_env()
    token = env.get("SUPABASE_ACCESS_TOKEN")
    ref = env.get("PROJECT_REF")
    if not token:
        raise SystemExit("請先在 .env.local 的 SUPABASE_ACCESS_TOKEN= 後面貼上 token")
    if not ref:
        raise SystemExit("請先在 .env.local 填入 PROJECT_REF")

    print("→ 取得 API 金鑰…")
    keys = req("GET", f"/v1/projects/{ref}/api-keys?reveal=true", token)
    anon = find_key(keys, "anon")
    service = find_key(keys, "service_role")
    if not anon:
        raise SystemExit("找不到 anon 金鑰。API 回應:" + json.dumps(keys, ensure_ascii=False)[:400])

    print("→ 寫入 app/config.js…")
    CONFIG.write_text(
        "// 由 scripts/supabase_setup.py 自動產生(不進 git)\n"
        "window.APP_CONFIG = {\n"
        f'  SUPABASE_URL: "https://{ref}.supabase.co",\n'
        f'  SUPABASE_ANON_KEY: "{anon}",\n'
        "};\n",
        encoding="utf-8",
    )

    print("→ 設定登入白名單(Site URL / Redirect URLs)…")
    req("PATCH", f"/v1/projects/{ref}/config/auth", token,
        {"site_url": SITE, "uri_allow_list": REDIRECTS})

    if service:
        print("→ 把 service_role 金鑰寫回 .env.local…")
        ENV.write_text(set_env_var(ENV.read_text(encoding="utf-8"), "SUPABASE_SERVICE_KEY", service), encoding="utf-8")

    print("\n[完成] config.js 已填好、登入白名單已設定。可以重開伺服器登入了。")


if __name__ == "__main__":
    main()
