import { api } from './api'

export interface AuthUser {
  id: number | string
  name: string
  email: string
  role: string
  created_at?: string
}

export interface AuthSession {
  access_token: string
  token_type?: string
  token?: string
  user: AuthUser
}

export const authService = {
  login: async (email: string, password: string): Promise<AuthSession> => {
    return api.post<AuthSession>('/api/auth/login', { email: email.trim().toLowerCase(), password })
  },
  register: async (payload: { name: string; email: string; password: string; role: string }): Promise<AuthUser> => {
    return api.post<AuthUser>('/api/auth/register', {
      name: payload.name.trim(),
      email: payload.email.trim().toLowerCase(),
      password: payload.password,
      role: payload.role.toLowerCase(),
    })
  },
  me: async (): Promise<AuthUser> => {
    return api.get<AuthUser>('/api/auth/me')
  },
  logout: async (): Promise<void> => {
    // Client-side token discard; no backend logout route required
    return Promise.resolve()
  },
}

export default authService
