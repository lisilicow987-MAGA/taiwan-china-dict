// Service Worker:network-first —— 連線時一律抓最新檔,離線才用快取。
// CACHE 版號由部署流程(deploy.yml)自動蓋成 commit SHA,確保每次部署都是新版,
// 觸發前端自動更新與重載。本機直接開時版號維持 placeholder,不影響功能。
const CACHE = "tw-dict-__CACHE_VERSION__";
const SHELL = [
  "./",
  "./index.html",
  "./styles.css",
  "./app.js",
  "./config.js",
  "./manifest.webmanifest",
  "./icon.svg",
];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(SHELL)).catch(() => {}).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  const url = new URL(req.url);
  // 只處理本網域 GET;跨網域(Supabase / CDN)交給瀏覽器直接處理
  if (req.method !== "GET" || url.origin !== self.location.origin) return;
  // network-first:先抓網路最新版並順手更新快取,失敗(離線)才回退快取
  e.respondWith(
    fetch(req)
      .then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
        return res;
      })
      .catch(() => caches.match(req).then((hit) => hit || caches.match("./index.html")))
  );
});
