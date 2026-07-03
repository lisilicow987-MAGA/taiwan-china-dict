// 複製本檔為 config.js,填入你的 Supabase 專案資訊。
//
// SUPABASE_ANON_KEY 是「可公開金鑰(anon/publishable)」,放在前端是 Supabase 的
// 正常設計——真正的安全靠資料表的 RLS 規則,不是靠藏這把 key。
// 但依本專案規範,config.js 已被 .gitignore 排除,不進 git。
//
// 取得位置:Supabase 專案 → Project Settings → API
//   Project URL  → SUPABASE_URL
//   anon public  → SUPABASE_ANON_KEY
window.APP_CONFIG = {
  SUPABASE_URL: "https://YOUR-PROJECT.supabase.co",
  SUPABASE_ANON_KEY: "YOUR-ANON-PUBLIC-KEY",
};
