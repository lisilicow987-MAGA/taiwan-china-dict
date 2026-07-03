# Edge Function:lookup(AI 建議台灣用語)

用 Google Gemini **免費** API,輸入中國用語 → 回傳台灣對應的「建議草稿」。
前端「🤖 AI 建議」按鈕呼叫它;答案一律當成建議,存進 App 後為「待查證」。

整套花費:**$0**(Supabase Edge Function 免費額度 + Gemini 免費層)。

## 一次性設定

### 1. 拿一把免費 Gemini 金鑰
1. 到 **https://aistudio.google.com/apikey**(Google AI Studio)
2. 用 Google 帳號登入 → **Create API key** → 複製(免綁信用卡)

### 2. 在 Supabase 建立這個函式
最簡單走**網頁**,不用裝任何工具:
1. Supabase 專案 → 左側 **Edge Functions** → **Create a function**(或 Deploy a new function)
2. 函式名稱填 **`lookup`**
3. 把本資料夾 `lookup/index.ts` 的內容**整段貼上** → **Deploy**

### 3. 設定金鑰(密鑰)
Supabase 專案 → **Edge Functions → Secrets**(或 Project Settings → Edge Functions):
- 新增一個密鑰:名稱 **`GEMINI_API_KEY`**,值貼上第 1 步的金鑰 → 儲存

> ⚠ 金鑰只填進 Supabase 密鑰,**不要貼到對話、不進 git**。函式以 `Deno.env.get("GEMINI_API_KEY")` 讀取。

### 4. 完成
回 App(已部署的網址)→ 在「中國用語」打字 → 按「🤖 AI 建議台灣用語」→
台灣對應與備註會自動填入 → 按「新增」存成**待查證** → 之後由你/Claude 查證升級。

## 備註
- 只有**登入的帳號**能呼叫(Edge Function 預設驗證 JWT;本專案已關閉開放註冊 → 等於只有你)。
- 免費模型準度不如 Claude,故所有 AI 答案都標「待查證」,以查證後為準。
- 若哪天 `gemini-2.0-flash` 模型名稱失效,改 `index.ts` 裡的 `MODEL` 常數即可。
