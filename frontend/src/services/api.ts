export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
export const TOKEN_KEY = 'mediscribe_access_token'

export class ApiError extends Error {
  status: number
  detail: string

  constructor(status: number, message: string, detail?: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail || message
  }
}

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY) || sessionStorage.getItem(TOKEN_KEY)
}

export function setStoredToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token)
  sessionStorage.setItem(TOKEN_KEY, token)
}

export function clearStoredToken() {
  localStorage.removeItem(TOKEN_KEY)
  sessionStorage.removeItem(TOKEN_KEY)
}

async function parseErrorResponse(response: Response): Promise<{ message: string; detail: string }> {
  try {
    const data = await response.json()
    if (typeof data.detail === 'string') {
      return { message: data.detail, detail: data.detail }
    } else if (Array.isArray(data.detail)) {
      const msg = data.detail.map((err: { msg?: string; loc?: string[] }) => err.msg || JSON.stringify(err)).join(', ')
      return { message: msg, detail: msg }
    } else if (data.message) {
      return { message: data.message, detail: data.message }
    }
  } catch {
    // response was not JSON
  }
  const text = await response.text().catch(() => '')
  const msg = text || `Request failed with status ${response.status}`
  return { message: msg, detail: msg }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)

  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const token = getStoredToken()
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  const url = `${API_BASE_URL}${normalizedPath}`

  const response = await fetch(url, { ...options, headers })

  if (response.status === 401) {
    clearStoredToken()
    window.dispatchEvent(new CustomEvent('mediscribe:unauthorized'))
    const err = await parseErrorResponse(response)
    throw new ApiError(401, err.message || 'Session expired. Please log in again.', err.detail)
  }

  if (response.status === 403) {
    const err = await parseErrorResponse(response)
    throw new ApiError(403, err.message || 'Permission denied.', err.detail)
  }

  if (!response.ok) {
    const err = await parseErrorResponse(response)
    throw new ApiError(response.status, err.message, err.detail)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}

export const apiRequest = <T>(path: string, options?: RequestInit) => request<T>(path, options)

export const apiMultipart = <T>(path: string, form: FormData, options: RequestInit = {}) => {
  // Let fetch handle Content-Type boundary automatically for FormData
  return request<T>(path, {
    ...options,
    method: options.method || 'POST',
    body: form,
  })
}

export const api = {
  get: <T>(path: string, options?: RequestInit) => request<T>(path, { ...options, method: 'GET' }),
  post: <T>(path: string, body?: unknown, options?: RequestInit) =>
    request<T>(path, {
      ...options,
      method: 'POST',
      body: body instanceof FormData ? body : body !== undefined ? JSON.stringify(body) : undefined,
    }),
  put: <T>(path: string, body?: unknown, options?: RequestInit) =>
    request<T>(path, {
      ...options,
      method: 'PUT',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),
  delete: <T>(path: string, options?: RequestInit) => request<T>(path, { ...options, method: 'DELETE' }),
}
