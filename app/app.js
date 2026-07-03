// ── 設定檢查 ──────────────────────────────────────────────
const cfg = window.APP_CONFIG;
const $ = (sel) => document.querySelector(sel);

if (!cfg) {
  $("#setup").hidden = false;
  throw new Error("尚未載入 config.js");
}

const DEMO = cfg.DEMO === true;

// ── 本機示範用的假後端(config.js 設 DEMO:true 時啟用,不連任何服務)──
const DEMO_SEED = [
  { tw: "影片", cn: "视频", category: "網路流行語", status: "confirmed", note: "★臺灣年輕人已大量改口說『視頻』而不自覺" },
  { tw: "馬上 / 立刻", cn: "立马", category: "網路流行語", status: "confirmed", note: "★『立馬』近年大量入侵臺灣口語" },
  { tw: "早安 / 早", cn: "早上好", category: "問候", status: "confirmed", note: "★臺灣習慣『早安』『早』" },
  { tw: "送出 / 提出 / 遞交", cn: "提交", category: "常用詞", status: "confirmed", note: "submit;查證:仲裁法用『提付』、公司法用『提案』,全文皆無『提交』" },
  { tw: "品質", cn: "质量", category: "常用詞", status: "confirmed", note: "⚠陷阱:中國『质量』=品質;臺灣『質量』=物理 mass" },
  { tw: "馬鈴薯", cn: "土豆", category: "飲食", status: "confirmed", note: "⚠陷阱:臺灣『土豆』=花生" },
  { tw: "種草 → 推坑 / 燒到", cn: "种草", category: "網路流行語", status: "confirmed", note: "小紅書核心詞" },
  { tw: "增能 / 加值", cn: "赋能", category: "職場黑話", status: "confirmed", note: "中國科技業黑話" },
  { tw: "計程車", cn: "出租车", category: "交通", status: "confirmed", note: "" },
  { tw: "鳳梨", cn: "菠萝", category: "飲食", status: "confirmed", note: "" },
  { tw: "外貌 / 長相", cn: "颜值", category: "網路流行語", status: "disputed", note: "是否該視為外來語仍有爭議,已半通用" },
  { tw: null, cn: "yyds", category: "網路流行語", status: "pending", note: null, source: "抖音留言" },
  { tw: null, cn: "退退退", category: "網路流行語", status: "pending", note: null, source: "小紅書" },
  { tw: null, cn: "绝绝子", category: "網路流行語", status: "pending", note: null, source: "短影音" },
];

function makeDemoClient() {
  let store = DEMO_SEED.map((e, i) => ({
    id: "demo-" + i, source: null, examples: null, note: null,
    created_at: new Date(Date.now() - i * 1000).toISOString(),
    updated_at: new Date(Date.now() - i * 1000).toISOString(),
    ...e,
  }));
  const ok = (data) => Promise.resolve({ data, error: null });
  const iso = () => new Date().toISOString();
  return {
    auth: {
      async getSession() { return { data: { session: { user: { email: "示範模式(本機假資料)" } } } }; },
      onAuthStateChange() { return { data: { subscription: { unsubscribe() {} } } }; },
      async signInWithOtp() { return { error: null }; },
      async signOut() { return { error: null }; },
    },
    channel() { const c = { on: () => c, subscribe: () => c }; return c; },
    from() {
      let op = "select", payload = null, fid = null, oKey = null, oAsc = true;
      const run = () => {
        if (op === "select") {
          let rows = [...store];
          if (oKey) rows.sort((a, b) => (a[oKey] > b[oKey] ? 1 : -1) * (oAsc ? 1 : -1));
          return ok(rows);
        }
        if (op === "insert") {
          (Array.isArray(payload) ? payload : [payload]).forEach((x) =>
            store.unshift({ id: "demo-" + Math.random().toString(36).slice(2), source: null, examples: null, note: null, created_at: iso(), updated_at: iso(), ...x }));
        } else if (op === "update") {
          store = store.map((r) => (r.id === fid ? { ...r, ...payload, updated_at: iso() } : r));
        } else if (op === "delete") {
          store = store.filter((r) => r.id !== fid);
        }
        return ok(null);
      };
      const b = {
        select() { op = "select"; return b; },
        insert(p) { op = "insert"; payload = p; return b; },
        update(p) { op = "update"; payload = p; return b; },
        delete() { op = "delete"; return b; },
        eq(_c, v) { fid = v; return b; },
        order(k, o) { oKey = k; oAsc = !(o && o.ascending === false); return run(); },
        then(res, rej) { return run().then(res, rej); },
      };
      return b;
    },
  };
}

let sb;
if (DEMO) {
  sb = makeDemoClient();
} else {
  if (!cfg.SUPABASE_URL || cfg.SUPABASE_URL.includes("YOUR-PROJECT")) {
    $("#setup").hidden = false;
    throw new Error("尚未設定 Supabase");
  }
  const { createClient } = await import("https://esm.sh/@supabase/supabase-js@2");
  sb = createClient(cfg.SUPABASE_URL, cfg.SUPABASE_ANON_KEY);
}

const STATUS_LABEL = { pending: "待查證", confirmed: "已確認", disputed: "有爭議" };

// ── 狀態 ──────────────────────────────────────────────────
let session = null;
let terms = [];
const filter = { q: "", status: "all", category: "all" };

// ── 工具 ──────────────────────────────────────────────────
function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(toast._t);
  toast._t = setTimeout(() => t.classList.remove("show"), 2200);
}
const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );

// ── 認證 ──────────────────────────────────────────────────
async function init() {
  const { data } = await sb.auth.getSession();
  session = data.session;
  sb.auth.onAuthStateChange((_e, s) => {
    session = s;
    renderAuth();
    if (s) loadTerms();
  });
  renderAuth();
  if (session) {
    await loadTerms();
    subscribeRealtime();
  }
}

function renderAuth() {
  const logged = !!session;
  $("#login").hidden = logged;
  $("#app").hidden = !logged;
  const bar = $("#userbar");
  if (logged) {
    bar.innerHTML = `<span>${esc(session.user.email)}</span>
      <button class="ghost" id="pwBtn">設定密碼</button>
      <button class="ghost" id="logoutBtn">登出</button>`;
    $("#pwBtn").onclick = async () => {
      const pw = prompt("設定登入密碼(至少 6 碼),之後即可用 Email + 密碼登入:");
      if (!pw) return;
      if (pw.length < 6) return toast("密碼至少 6 碼");
      const { error } = await sb.auth.updateUser({ password: pw });
      toast(error ? "設定失敗:" + error.message : "密碼已設定!手機可用 Email+密碼登入");
    };
    $("#logoutBtn").onclick = async () => {
      await sb.auth.signOut();
      terms = [];
    };
  } else {
    bar.innerHTML = "";
  }
}

let authMode = "signin"; // signin | signup
$("#toggleMode").onclick = () => {
  authMode = authMode === "signin" ? "signup" : "signin";
  $("#loginTitle").textContent = authMode === "signin" ? "登入" : "建立帳號";
  $("#loginBtn").textContent = authMode === "signin" ? "登入" : "建立帳號";
  $("#toggleMode").textContent = authMode === "signin" ? "第一次使用?建立帳號" : "已有帳號?改為登入";
  $("#loginMsg").textContent = "";
};

$("#loginBtn").onclick = async () => {
  const email = $("#email").value.trim();
  const password = $("#password").value;
  if (!email || !password) return toast("請輸入 Email 與密碼");
  if (password.length < 6) return toast("密碼至少 6 碼");
  $("#loginBtn").disabled = true;
  let error;
  if (authMode === "signup") {
    const res = await sb.auth.signUp({ email, password });
    error = res.error;
    if (!error && !res.data.session) {
      $("#loginMsg").textContent = "帳號已建立,但專案仍要求 Email 確認。請到 Supabase 關閉 Confirm email 後,改用「登入」。";
      $("#loginBtn").disabled = false;
      return;
    }
  } else {
    const res = await sb.auth.signInWithPassword({ email, password });
    error = res.error;
  }
  $("#loginBtn").disabled = false;
  $("#loginMsg").textContent = error ? "失敗:" + error.message : "";
};

// ── 資料存取 ──────────────────────────────────────────────
async function loadTerms() {
  const { data, error } = await sb
    .from("terms")
    .select("*")
    .order("updated_at", { ascending: false });
  if (error) return toast("讀取失敗:" + error.message);
  terms = data || [];
  render();
}

async function addTerm(payload) {
  const { error } = await sb.from("terms").insert(payload);
  if (error) return toast("新增失敗:" + error.message);
  toast("已新增");
  await loadTerms();
}

async function updateTerm(id, patch) {
  const { error } = await sb.from("terms").update(patch).eq("id", id);
  if (error) return toast("更新失敗:" + error.message);
  toast("已更新");
  await loadTerms();
}

async function deleteTerm(id) {
  const { error } = await sb.from("terms").delete().eq("id", id);
  if (error) return toast("刪除失敗:" + error.message);
  toast("已刪除");
  await loadTerms();
}

function subscribeRealtime() {
  sb.channel("terms-changes")
    .on("postgres_changes", { event: "*", schema: "public", table: "terms" }, () => loadTerms())
    .subscribe();
}

// ── 新增表單 ──────────────────────────────────────────────
// ── 重複偵測(含簡繁正規化,解決 立马/立馬、视频/視頻 這類漏抓)──
// 用 opencc-js 把兩邊都折成簡體再比;載入前先以「去空白」為後備,載入後重算提示。
let _foldFn = (s) => (s || "").trim();
const _foldCache = new Map();
function fold(s) {
  s = (s || "").trim();
  if (_foldCache.has(s)) return _foldCache.get(s);
  const v = _foldFn(s);
  _foldCache.set(s, v);
  return v;
}
import("https://esm.sh/opencc-js@1.0.5")
  .then((mod) => {
    const Converter = mod.Converter || (mod.default && mod.default.Converter);
    if (!Converter) return;
    const conv = Converter({ from: "t", to: "cn" }); // 繁→簡
    _foldFn = (s) => conv((s || "").trim());
    _foldCache.clear(); // 清掉後備期間算過的舊值
    updateDupHint();
  })
  .catch(() => {});

function findDup(cn) {
  const k = fold(cn);
  return k ? terms.find((t) => fold(t.cn) === k) : null;
}
function hideDupHint() {
  const h = $("#dupHint");
  h.hidden = true;
  h.textContent = "";
}
function updateDupHint() {
  const el = $("#addForm") && $("#addForm").cn;
  if (!el) return;
  const dup = findDup(el.value);
  if (dup) {
    const h = $("#dupHint");
    h.hidden = false;
    h.textContent = `⚠ 已存在:${dup.cn} ↔ ${dup.tw || "(臺灣對應待補)"}(${STATUS_LABEL[dup.status] || dup.status})`;
  } else {
    hideDupHint();
  }
}

$("#addForm").addEventListener("submit", (e) => {
  e.preventDefault();
  const f = e.target;
  const cn = f.cn.value.trim();
  if (!cn) return toast("「中國用語」必填");
  const dup = findDup(cn);
  if (dup) {
    const ok = confirm(
      `「${cn}」可能已存在:\n${dup.cn} ↔ ${dup.tw || "(臺灣對應待補)"}(${STATUS_LABEL[dup.status] || dup.status})\n\n仍要新增嗎?`
    );
    if (!ok) return;
  }
  addTerm({
    cn,
    tw: f.tw.value.trim() || null,
    category: f.category.value.trim() || "未分類",
    source: f.source.value.trim() || null,
    note: f.note.value.trim() || null,
    status: "pending",
  });
  f.reset();
  hideDupHint();
  f.cn.focus();
});

$("#addForm").cn.addEventListener("input", updateDupHint);

// 清除表單
$("#clearBtn").onclick = () => {
  $("#addForm").reset();
  hideDupHint();
  $("#addForm").cn.focus();
};

// ── AI 建議(呼叫 lookup Edge Function → 填入臺灣對應,存成待查證)──
$("#aiBtn").onclick = async () => {
  if (DEMO) return toast("示範模式不支援 AI 查詢(需連上真後端)");
  const f = $("#addForm");
  const cn = f.cn.value.trim();
  if (!cn) return toast("請先填「中國用語」");
  const btn = $("#aiBtn");
  const label = btn.textContent;
  btn.disabled = true;
  btn.textContent = "AI 查詢中…";
  const { data, error } = await sb.functions.invoke("lookup", { body: { term: cn, direction: "cn2tw" } });
  btn.disabled = false;
  btn.textContent = label;
  if (error || (data && data.error)) {
    return toast("查詢失敗:" + ((data && data.error) || error.message));
  }
  if (data.tw) f.tw.value = data.tw;
  const conf = data.confidence ? `(AI 信心:${data.confidence})` : "";
  f.note.value = (data.note ? data.note : "") + conf;
  if (!f.source.value) f.source.value = data.source || "AI 建議";
  toast("已填入 AI 建議,按「新增」會存成待查證");
};

// ── 搜尋 / 篩選 ──────────────────────────────────────────
$("#search").addEventListener("input", (e) => {
  filter.q = e.target.value.trim().toLowerCase();
  render();
});

function categories() {
  return [...new Set(terms.map((t) => t.category || "未分類"))].sort();
}

function renderChips() {
  const chips = $("#chips");
  const statusBtns = [["all", "全部"], ["pending", "待查證"], ["confirmed", "已確認"], ["disputed", "有爭議"]]
    .map(([v, l]) => `<button class="chip ${filter.status === v ? "active" : ""}" data-status="${v}">${l}</button>`)
    .join("");
  const catOpts = ['<option value="all">所有分類</option>']
    .concat(categories().map((c) => `<option value="${esc(c)}" ${filter.category === c ? "selected" : ""}>${esc(c)}</option>`))
    .join("");
  chips.innerHTML = statusBtns + `<select id="catFilter" style="width:auto">${catOpts}</select>`;
  chips.querySelectorAll("[data-status]").forEach((b) => {
    b.onclick = () => { filter.status = b.dataset.status; render(); };
  });
  $("#catFilter").onchange = (e) => { filter.category = e.target.value; render(); };
}

function matches(t) {
  if (filter.status !== "all" && t.status !== filter.status) return false;
  if (filter.category !== "all" && (t.category || "未分類") !== filter.category) return false;
  if (filter.q) {
    const hay = [t.tw, t.cn, t.note, t.source, t.category].join(" ").toLowerCase();
    if (!hay.includes(filter.q)) return false;
  }
  return true;
}

// ── 渲染列表 ──────────────────────────────────────────────
function render() {
  renderChips();
  $("#catList").innerHTML = categories().map((c) => `<option value="${esc(c)}">`).join("");

  const rows = terms.filter(matches);
  $("#count").textContent = `共 ${terms.length} 筆,符合 ${rows.length} 筆`;

  $("#list").innerHTML = rows
    .map((t) => {
      const tw = t.tw
        ? `<span class="tw">${esc(t.tw)}</span>`
        : `<span class="tw empty">（臺灣對應待補）</span>`;
      return `<li class="card" data-id="${t.id}">
        <div class="pair">${tw}<span class="arrow">↔</span><span class="cn">${esc(t.cn)}</span></div>
        <div class="meta">
          <span class="badge cat">${esc(t.category || "未分類")}</span>
          <span class="badge ${t.status}">${STATUS_LABEL[t.status] || t.status}</span>
        </div>
        ${t.note ? `<div class="note">${esc(t.note)}</div>` : ""}
        ${t.source ? `<div class="src">來源:${esc(t.source)}</div>` : ""}
        <div class="actions">
          <button class="ghost" data-act="edit">編輯</button>
          ${t.status !== "confirmed" ? `<button class="ghost" data-act="confirm">✓ 升為已確認</button>` : ""}
          <button class="danger" data-act="del">刪除</button>
        </div>
      </li>`;
    })
    .join("") || `<li class="hint" style="padding:24px;text-align:center">沒有符合的詞</li>`;

  $("#list").querySelectorAll(".card").forEach((card) => {
    const id = card.dataset.id;
    const t = terms.find((x) => x.id === id);
    card.querySelector('[data-act="edit"]').onclick = () => openEdit(t);
    card.querySelector('[data-act="del"]').onclick = () => {
      if (confirm(`確定刪除「${t.cn}」?`)) deleteTerm(id);
    };
    const cbtn = card.querySelector('[data-act="confirm"]');
    if (cbtn) cbtn.onclick = () => updateTerm(id, { status: "confirmed" });
  });
}

// ── 編輯燈箱 ──────────────────────────────────────────────
function openEdit(t) {
  const root = $("#modalRoot");
  root.innerHTML = `
    <div class="modal-backdrop">
      <div class="modal">
        <h2>編輯詞條</h2>
        <label>臺灣用語<input id="m_tw" value="${esc(t.tw)}" placeholder="臺灣對應"></label>
        <label>中國用語 *<input id="m_cn" value="${esc(t.cn)}"></label>
        <div class="row">
          <label>分類<input id="m_cat" list="catList" value="${esc(t.category || "未分類")}"></label>
          <label>狀態
            <select id="m_status">
              ${["pending", "confirmed", "disputed"].map((s) => `<option value="${s}" ${t.status === s ? "selected" : ""}>${STATUS_LABEL[s]}</option>`).join("")}
            </select>
          </label>
        </div>
        <label>來源<input id="m_src" value="${esc(t.source)}" placeholder="在哪聽到的"></label>
        <label>例句<textarea id="m_ex" rows="2" placeholder="例句">${esc(t.examples)}</textarea></label>
        <label>備註<textarea id="m_note" rows="2" placeholder="備註 / 陷阱">${esc(t.note)}</textarea></label>
        <div class="row">
          <button class="ghost" id="m_cancel">取消</button>
          <button class="primary" id="m_save">儲存</button>
        </div>
      </div>
    </div>`;
  const close = () => (root.innerHTML = "");
  root.querySelector(".modal-backdrop").onclick = (e) => { if (e.target.classList.contains("modal-backdrop")) close(); };
  $("#m_cancel").onclick = close;
  $("#m_save").onclick = async () => {
    const cn = $("#m_cn").value.trim();
    if (!cn) return toast("「中國用語」必填");
    await updateTerm(t.id, {
      tw: $("#m_tw").value.trim() || null,
      cn,
      category: $("#m_cat").value.trim() || "未分類",
      status: $("#m_status").value,
      source: $("#m_src").value.trim() || null,
      examples: $("#m_ex").value.trim() || null,
      note: $("#m_note").value.trim() || null,
    });
    close();
  };
}

// ── 註冊 Service Worker + 自動更新 ────────────────────────
// 部署新版後,前端會自動偵測到新的 SW 並在背景切換,切換完成即自動重載,
// 使用者不必手動重整。
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("./sw.js", { updateViaCache: "none" }).then((reg) => {
    reg.update();
    setInterval(() => reg.update(), 60 * 1000);          // 每分鐘檢查新版
    document.addEventListener("visibilitychange", () => {  // 回到 App 時也檢查
      if (document.visibilityState === "visible") reg.update();
    });
  }).catch(() => {});

  let refreshing = false;
  navigator.serviceWorker.addEventListener("controllerchange", () => {
    if (refreshing) return;                               // 避免重載迴圈
    refreshing = true;
    location.reload();
  });
}

init();
