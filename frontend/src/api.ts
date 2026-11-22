import type {
  CreatedProject,
  FlakyTest,
  Project,
  RunList,
  Statistics,
  TestRunDetails,
  TokenResponse,
  User,
} from './types'

const API_ROOT = '/api/v1'

interface RequestOptions extends Omit<RequestInit, 'body'> {
  token?: string
  body?: unknown
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { token, body, headers: requestHeaders, ...init } = options
  const headers = new Headers(requestHeaders)
  headers.set('Accept', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)

  let requestBody: BodyInit | undefined
  if (body instanceof FormData) {
    requestBody = body
  } else if (body !== undefined) {
    headers.set('Content-Type', 'application/json')
    requestBody = JSON.stringify(body)
  }

  const response = await fetch(`${API_ROOT}${path}`, {
    ...init,
    headers,
    body: requestBody,
  })

  if (!response.ok) {
    let message = `Request failed (${response.status})`
    try {
      const payload: { detail?: string | { msg?: string }[] } = await response.json()
      if (typeof payload.detail === 'string') message = payload.detail
      if (Array.isArray(payload.detail)) {
        message = payload.detail.map((item) => item.msg).filter(Boolean).join('; ') || message
      }
    } catch {
      message = `${message}. Check your connection to the server.`
    }
    throw new Error(message)
  }

  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const api = {
  register: (body: { email: string; display_name: string; password: string }) =>
    request<User>('/auth/register', { method: 'POST', body }),
  login: (body: { email: string; password: string }) =>
    request<TokenResponse>('/auth/login', { method: 'POST', body }),
  me: (token: string, signal?: AbortSignal) =>
    request<User>('/auth/me', { token, signal }),
  projects: (token: string, signal?: AbortSignal) =>
    request<Project[]>('/projects', { token, signal }),
  createProject: (token: string, body: { name: string; description: string }) =>
    request<CreatedProject>('/projects', { token, method: 'POST', body }),
  updateProject: (
    token: string,
    id: string,
    body: { name: string; description: string },
  ) => request<Project>(`/projects/${id}`, { token, method: 'PATCH', body }),
  deleteProject: (token: string, id: string) =>
    request<void>(`/projects/${id}`, { token, method: 'DELETE' }),
  statistics: (token: string, id: string, signal?: AbortSignal) =>
    request<Statistics>(`/projects/${id}/statistics`, { token, signal }),
  runs: (token: string, id: string, signal?: AbortSignal) =>
    request<RunList>(`/projects/${id}/runs?limit=8`, { token, signal }),
  flakyTests: (token: string, id: string, signal?: AbortSignal) =>
    request<FlakyTest[]>(`/projects/${id}/flaky-tests?limit=8`, { token, signal }),
  run: (token: string, id: string) => request<TestRunDetails>(`/runs/${id}`, { token }),
  upload: (token: string, projectId: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request(`/projects/${projectId}/runs`, {
      token,
      method: 'POST',
      body: form,
    })
  },
}
