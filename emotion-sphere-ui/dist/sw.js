// 每次部署新版本时更新此版本号（或 CI 自动替换）
const CACHE_VERSION = '20250509-1200'
const CACHE_NAME = `emotion-sphere-${CACHE_VERSION}`

self.addEventListener('install', (event) => {
  // 新 SW 立即激活，不等旧页面关闭
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  // 删除所有旧版缓存
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))),
    ),
  )
  self.clients.claim()
})

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') {
    return
  }

  // Network-first：先请求网络，失败再用缓存
  event.respondWith(
    fetch(event.request)
      .then((networkResponse) => {
        // 缓存成功的同源响应
        if (networkResponse.ok && event.request.url.startsWith(self.location.origin)) {
          const cloned = networkResponse.clone()
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, cloned))
        }
        return networkResponse
      })
      .catch(() => caches.match(event.request).then((cached) => cached || caches.match('/index.html'))),
  )
})
