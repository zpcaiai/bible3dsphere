import { useEffect, useState } from 'react'
import { fetchCurrentUser, getCachedUser, logout, setCachedUser, clearToken } from '../auth'

export function useAuth() {
  const [user, setUser] = useState(() => getCachedUser())
  const [authLoading, setAuthLoading] = useState(true)

  useEffect(() => {
    fetchCurrentUser().then((u) => {
      setUser(u)
      setAuthLoading(false)
    })
  }, [])

  const handleLogout = async () => {
    await logout()
    setUser(null)
  }

  const updateUser = (u) => {
    setUser(u)
    if (u) {
      setCachedUser(u)
    } else {
      clearToken()
    }
  }

  return { user, authLoading, setUser: updateUser, handleLogout }
}
