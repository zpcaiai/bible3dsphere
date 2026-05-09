let deferredPrompt = null

export function registerServiceWorker() {
  if (!('serviceWorker' in navigator)) {
    return
  }

  window.addEventListener('load', async () => {
    try {
      const reg = await navigator.serviceWorker.register('/sw.js', { updateViaCache: 'none' })
      // 检测到新版 SW 时立即刷新页面
      reg.addEventListener('updatefound', () => {
        const newSW = reg.installing
        if (newSW) {
          newSW.addEventListener('statechange', () => {
            if (newSW.state === 'activated' && navigator.serviceWorker.controller) {
              window.location.reload()
            }
          })
        }
      })
    } catch (error) {
      console.error('Service worker registration failed:', error)
    }
  })
}

export function subscribeToInstallPrompt(callback) {
  function handleBeforeInstallPrompt(event) {
    event.preventDefault()
    deferredPrompt = event
    callback(true)
  }

  function handleAppInstalled() {
    deferredPrompt = null
    callback(false)
  }

  window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt)
  window.addEventListener('appinstalled', handleAppInstalled)

  return () => {
    window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt)
    window.removeEventListener('appinstalled', handleAppInstalled)
  }
}

export async function promptInstall() {
  if (!deferredPrompt) {
    return false
  }

  deferredPrompt.prompt()
  const choice = await deferredPrompt.userChoice
  deferredPrompt = null
  return choice?.outcome === 'accepted'
}

export function isIosInstallable() {
  if (typeof window === 'undefined') {
    return false
  }

  const userAgent = window.navigator.userAgent || ''
  const isIos = /iphone|ipad|ipod/i.test(userAgent)
  const isStandalone = window.navigator.standalone === true
  return isIos && !isStandalone
}
