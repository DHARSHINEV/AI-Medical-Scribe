import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import authService, { type AuthUser } from '../services/authService'
import { clearStoredToken, getStoredToken, setStoredToken } from '../services/api'

export type AuthMode = 'live' | 'demo'

interface AuthState {
  user: AuthUser | null
  mode: AuthMode
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
  login: (email: string, password: string) => Promise<boolean>
  register: (payload: { name: string; email: string; password: string; role: string }) => Promise<boolean>
  logout: () => Promise<void>
  refreshUser: () => Promise<void>
  enterDemoMode: () => void
}

const AuthContext = createContext<AuthState | undefined>(undefined)

const DEMO_USER: AuthUser = {
  id: 'demo-doctor',
  name: 'Dr. Sarah Jenkins',
  email: 'demo@mediscribe.synthetic',
  role: 'doctor',
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [mode, setMode] = useState<AuthMode>('live')
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true

    const verifySession = async () => {
      const token = getStoredToken()
      if (!token) {
        if (mounted) setIsLoading(false)
        return
      }

      try {
        const clinician = await authService.me()
        if (mounted) {
          setUser(clinician)
          setMode('live')
        }
      } catch {
        if (mounted) {
          clearStoredToken()
          setUser(null)
        }
      } finally {
        if (mounted) setIsLoading(false)
      }
    }

    verifySession()

    const handleUnauthorized = () => {
      if (mounted) {
        clearStoredToken()
        setUser(null)
      }
    }

    window.addEventListener('mediscribe:unauthorized', handleUnauthorized)
    return () => {
      mounted = false
      window.removeEventListener('mediscribe:unauthorized', handleUnauthorized)
    }
  }, [])

  const login = async (email: string, password: string): Promise<boolean> => {
    setIsLoading(true)
    setError(null)
    try {
      const session = await authService.login(email, password)
      const token = session.access_token || session.token
      if (token) {
        setStoredToken(token)
      }
      setUser(session.user)
      setMode('live')
      return true
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Unable to sign in.'
      setError(message)
      return false
    } finally {
      setIsLoading(false)
    }
  }

  const register = async (payload: { name: string; email: string; password: string; role: string }): Promise<boolean> => {
    setIsLoading(true)
    setError(null)
    try {
      const newUser = await authService.register(payload)
      // Automatically login after successful registration
      return await login(payload.email, payload.password)
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Unable to register.'
      setError(message)
      return false
    } finally {
      setIsLoading(false)
    }
  }

  const logout = async (): Promise<void> => {
    try {
      await authService.logout()
    } catch {
      // ignore
    }
    clearStoredToken()
    setUser(null)
    setMode('live')
    setError(null)
  }

  const refreshUser = async (): Promise<void> => {
    if (mode === 'demo') return
    try {
      const current = await authService.me()
      setUser(current)
    } catch {
      setUser(null)
    }
  }

  const enterDemoMode = () => {
    clearStoredToken()
    setUser(DEMO_USER)
    setMode('demo')
    setError(null)
  }

  const value = useMemo(
    () => ({
      user,
      mode,
      isAuthenticated: !!user,
      isLoading,
      error,
      login,
      register,
      logout,
      refreshUser,
      enterDemoMode,
    }),
    [user, mode, isLoading, error]
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within AuthProvider')
  return context
}
