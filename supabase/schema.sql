-- 台灣 vs 中國 用語對照辭典 — Supabase 資料表結構
-- 用法:在 Supabase 專案 → SQL Editor → 貼上整段 → Run(只需執行一次)

create extension if not exists "pgcrypto";

-- ── 主資料表 ───────────────────────────────────────────────
create table if not exists public.terms (
  id          uuid primary key default gen_random_uuid(),
  tw          text,                       -- 台灣用語(status=pending 時可先留空)
  cn          text not null,              -- 中國用語(隨手捕捉的主體)
  category    text not null default '未分類',
  status      text not null default 'pending'
              check (status in ('pending','confirmed','disputed')),
  source      text,                       -- 在哪聽到的(抖音/某影片…)
  examples    text,                       -- 例句
  note        text,                       -- 備註 / 陷阱說明
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

create index if not exists terms_cn_idx       on public.terms (cn);
create index if not exists terms_tw_idx       on public.terms (tw);
create index if not exists terms_status_idx   on public.terms (status);
create index if not exists terms_category_idx on public.terms (category);

-- ── updated_at 自動更新 ────────────────────────────────────
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end; $$;

drop trigger if exists terms_set_updated_at on public.terms;
create trigger terms_set_updated_at
  before update on public.terms
  for each row execute function public.set_updated_at();

-- ── Row Level Security(為「將來公開」預先設計好)─────────────
alter table public.terms enable row level security;

-- 未登入訪客:只能讀「已確認」的詞(將來公開查詢用)
drop policy if exists "anon read confirmed" on public.terms;
create policy "anon read confirmed"
  on public.terms for select to anon
  using (status = 'confirmed');

-- 登入者(你):可讀全部
drop policy if exists "auth read all" on public.terms;
create policy "auth read all"
  on public.terms for select to authenticated
  using (true);

-- 登入者:可新增 / 修改 / 刪除
drop policy if exists "auth insert" on public.terms;
create policy "auth insert" on public.terms for insert to authenticated
  with check (true);

drop policy if exists "auth update" on public.terms;
create policy "auth update" on public.terms for update to authenticated
  using (true) with check (true);

drop policy if exists "auth delete" on public.terms;
create policy "auth delete" on public.terms for delete to authenticated
  using (true);

-- ── 開啟 Realtime(多裝置即時同步)────────────────────────────
-- 若這行報錯說已存在,可忽略
alter publication supabase_realtime add table public.terms;
