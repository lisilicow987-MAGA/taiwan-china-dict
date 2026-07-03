# 臺灣用語辭典 — PWA(手機 App)

捕捉優先的對照辭典:在手機上隨手記下聽到的中國用語(預設「待查證」),
之後在桌機補上臺灣對應、查證、升為「已確認」。資料存在 Supabase,
可一鍵匯回 `dict/terms.json` 進 git 永久保存。

## 架構

```
app/            可安裝的 PWA(純前端,免 build)
supabase/       schema.sql(資料表+權限)、seed.sql(初始 193 筆)
scripts/        gen_seed.py(產 seed)、export_terms.py(雲端→git)
dict/           terms.json 永久檔案庫 + build.py(產 CSV/MD)
```

## 一次性建置步驟

### 1. 建 Supabase 專案
1. 到 supabase.com 註冊 → New project(免費方案即可)。
2. 進專案 → **SQL Editor** → 貼上 `supabase/schema.sql` → Run。
3. 重新產生種子並匯入:本機跑 `python scripts/gen_seed.py`,
   把產出的 `supabase/seed.sql` 貼進 SQL Editor → Run(匯入現有 193 筆)。

### 2. 設定前端
1. 複製 `app/config.example.js` 為 `app/config.js`。
2. 到 Supabase → **Project Settings → API**,把
   `Project URL` 與 `anon public` 填進 `config.js`。
   （anon key 是可公開金鑰,靠 RLS 保護;config.js 已被 .gitignore 排除。)

### 3. 開啟 Email 登入
Supabase → **Authentication → Providers → Email** 確認啟用
(預設開啟 magic link / OTP 即可)。

### 4. 本機試跑
在 `app/` 目錄起一個簡單伺服器(PWA 不能用 file:// 開):
```bash
cd app
python -m http.server 5173
```
瀏覽器開 http://localhost:5173 → 輸入 Email → 收信點連結登入。

### 5. 部署上線(手機安裝)
把 `app/` 推到任一靜態主機(GitHub Pages / Vercel / Netlify),
手機用瀏覽器開網址 → 選單「加到主畫面」即成 App。
> 部署網域記得加進 Supabase → Authentication → URL Configuration 的
> Redirect URLs,magic link 才會導回。

## 日常流程

- **隨手記**:手機 App 打開 → 填中國用語 → 存(待查證)。
- **查證**:把待查證清單丟給 Claude,補臺灣對應、例句、升為已確認。
- **回存 git**:`python scripts/export_terms.py` → `python dict/build.py`
  → 已確認的詞同步回 `terms.json` 並更新 CSV/Markdown。

## 待強化(下一版可做)

- 離線「先存本機、連線後自動同步」的佇列
- PNG 圖示(目前用 SVG,部分裝置桌面圖示較陽春)
- 公開唯讀頁(把 confirmed 詞開放給所有人查)
