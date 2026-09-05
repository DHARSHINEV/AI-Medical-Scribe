import { api } from './api'

export interface AuthUser { id: string; name: string; email: string; role: string }
export interface AuthSession { user: AuthUser; token?: string }

export const authService = {
  login: (email: string, password: string) => api.post<AuthSession>('/auth/login', { email, password }),
  register: (payload: { name: string; email: string; password: string; role: string }) => api.post<AuthSession>('/auth/register', payload),
  me: () => api.get<AuthUser>('/auth/me'),
  logout: () => api.post<void>('/auth/logout', {}),
}
export default authService
