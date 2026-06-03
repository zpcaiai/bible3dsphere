// emotion-sphere-2025 — Service Worker v3
// Cache name includes a version token — change it to bust all caches on next deploy
const CACHE_VERSION = 'emotion-sphere-2025-v3'
const ASSET_EXTS = ['.js', '.css', '.woff2', '.woff', '.ttf', '.png', '.svg', '.ico', '.webp', '.json']

// ─── Install: claim clients immediately ───────────────────────────────────────
self.addEventListener('install', event => {
  self.skipWaiting()
})

// ─── Activate: delete every cache that isn't the current version ──────────────
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(k => k !== CACHE_VERSION)
          .map(k => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  )
})

// ─── Fetch ────────────────────────────────────────────────────────────────────
self.addEventListener('fetch', event => {
  const req = event.request
  const url = new URL(req.url)

  // 1. Skip non-GET requests entirely — let the browser handle them natively
  if (req.method !== 'GET') return

  // 2. Skip cross-origin requests (Google Fonts, CDN, HuggingFace API, etc.)
  //    Attempting to cache or intercept cross-origin opaque responses causes
  //    "Failed to convert value to 'Response'" TypeErrors in older SW code.
  if (url.origin !== self.location.origin) return

  // 3. Skip API calls — always go to network
  if (url.pathname.startsWith('/api/')) return

  // 4. HTML navigation → network-first (prevents stale chunk problem)
  //    If the network is unavailable, fall back to the cached shell.
  if (req.mode === 'navigate' || req.headers.get('Accept')?.includes('text/html')) {
    event.respondWith(networkFirstHTML(req))
    return
  }

  // 5. Versioned JS/CSS/font assets → cache-first (safe because hash is in filename)
  const ext = url.pathname.substring(url.pathname.lastIndexOf('.'))
  if (ASSET_EXTS.includes(ext)) {
    event.respondWith(cacheFirstAsset(req))
    return
  }

  // 6. Everything else → network, no caching
})

// ─── Strategies ───────────────────────────────────────────────────────────────

async function networkFirstHTML(req) {
  try {
    const networkRes = await fetch(req)
    if (networkRes.ok) {
      const cache = await caches.open(CACHE_VERSION)
      cache.put(req, networkRes.clone())
    }
    return networkRes
  } catch {
    const cached = await caches.match(req)
    if (cached) return cached
    // Absolute fallback: serve cached root index if specific nav fails
    const root = await caches.match('/')
    if (root) return root
    return new Response('<h1>Offline</h1>', { headers: { 'Content-Type': 'text/html' } })
  }
}

async function cacheFirstAsset(req) {
  const cached = await caches.match(req)
  if (cached) return cached
  try {
    const networkRes = await fetch(req)
    if (networkRes.ok) {
      const cache = await caches.open(CACHE_VERSION)
      cache.put(req, networkRes.clone())
    }
    return networkRes
  } catch {
    return new Response('', { status: 503 })
  }
}

// ─── Web Push: 显示通知 ────────────────────────────────────────────────────────
self.addEventListener('push', event => {
  let payload = { title: '情感星球', body: '有一条新的提醒', url: '/' }
  try { if (event.data) payload = { ...payload, ...event.data.json() } } catch (e) {}
  event.waitUntil(
    self.registration.showNotification(payload.title, {
      body: payload.body,
      icon: '/favicon.svg',
      badge: '/favicon.svg',
      data: { url: payload.url || '/' },
      tag: payload.tag || 'reminder',
    })
  )
})

// ─── 点击通知 → 聚焦/打开应用 ──────────────────────────────────────────────────
self.addEventListener('notificationclick', event => {
  event.notification.close()
  const url = (event.notification.data && event.notification.data.url) || '/'
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
      for (const c of list) { if ('focus' in c) { c.navigate(url); return c.focus() } }
      if (clients.openWindow) return clients.openWindow(url)
    })
  )
})
