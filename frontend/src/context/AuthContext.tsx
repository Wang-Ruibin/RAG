import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api, authToken } from '../lib/api'
import type { User } from '../types'

interface AuthValue {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (name: string, email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthValue | null>(null)

interface TokenResult {
  access_token: string
  user: User
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(() => Boolean(authToken.get()))

  useEffect(() => {
    if (!authToken.get()) return
    api<User>('/api/auth/me')
      .then(setUser)
      .catch(() => authToken.clear())
      .finally(() => setLoading(false))
  }, [])

  async function authenticate(path: string, body: object) {
    const result = await api<TokenResult>(path, { method: 'POST', body: JSON.stringify(body) })
    authToken.set(result.access_token)
    setUser(result.user)
  }

  const value = useMemo<AuthValue>(
    () => ({
      user,
      loading,
      login: (email, password) => authenticate('/api/auth/login', { email, password }),
      register: (name, email, password) =>
        authenticate('/api/auth/register', { name, email, password }),
      logout: () => {
        authToken.clear()
        setUser(null)
      },
    }),
    [user, loading],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used inside AuthProvider')
  return value
}
