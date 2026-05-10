const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export interface ModerationItem {
  id: string
  case_event_id: string
  status: 'PENDING' | 'APPROVED' | 'REJECTED'
  created_at: string
  event_type: string
  event_date: string | null
  summary: string
  confidence_score: number
  source_attribution: Array<{ source_code: string; source_name: string }>
  source_quote: string | null
}

export interface AuditLogEntry {
  id: string
  user_id: string | null
  action: string
  resource_type: string
  resource_id: string | null
  ip_address: string | null
  created_at: string
}

export interface Source {
  id: string
  source_code: string
  source_name: string
  source_type: string
  language_code: string
  trust_score: number
  is_active: boolean
  last_fetched_at: string | null
  created_at: string
}

export interface AdminCaseSummary {
  id: string
  case_ref: string
  crime_category: string
  status: string
  state: string
  district: string
  is_suppressed: boolean
  event_count: number
  overall_confidence: number | null
  created_at: string
  updated_at: string
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
  }
}

export function getAuthHeaders(token: string): HeadersInit {
  return { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
}

async function apiFetch<T>(
  path: string,
  token: string,
  options?: RequestInit,
  params?: Record<string, string | number | boolean | undefined>,
): Promise<T> {
  const url = new URL(`${API_BASE}${path}`)
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined) url.searchParams.set(k, String(v))
    })
  }
  const res = await fetch(url.toString(), {
    ...options,
    headers: { ...getAuthHeaders(token), ...(options?.headers ?? {}) },
    cache: 'no-store',
  })
  if (!res.ok) {
    const body = await res.text().catch(() => '')
    throw new ApiError(res.status, body || `HTTP ${res.status}`)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export function makeAdminApi(token: string) {
  return {
    moderation: {
      list: (params?: { status?: string; page?: number; page_size?: number }) =>
        apiFetch<{ items: ModerationItem[]; total: number }>(
          '/v1/moderation/queue',
          token,
          undefined,
          params as Record<string, string | number | boolean | undefined>,
        ),
      approve: (id: string, notes?: string) =>
        apiFetch<void>(`/v1/moderation/${id}/approve`, token, {
          method: 'POST',
          body: JSON.stringify({ notes }),
        }),
      reject: (id: string, reason: string) =>
        apiFetch<void>(`/v1/moderation/${id}/reject`, token, {
          method: 'POST',
          body: JSON.stringify({ reason }),
        }),
    },
    cases: {
      list: (params?: { page?: number; page_size?: number; state?: string }) =>
        apiFetch<{ items: AdminCaseSummary[]; total: number }>(
          '/v1/cases',
          token,
          undefined,
          params as Record<string, string | number | boolean | undefined>,
        ),
      suppress: (id: string, reason: string) =>
        apiFetch<void>(`/v1/admin/cases/${id}/suppress`, token, {
          method: 'POST',
          body: JSON.stringify({ reason }),
        }),
    },
    sources: {
      list: () => apiFetch<Source[]>('/v1/admin/sources', token),
      create: (data: Partial<Source>) =>
        apiFetch<Source>('/v1/admin/sources', token, {
          method: 'POST',
          body: JSON.stringify(data),
        }),
      update: (id: string, data: Partial<Source>) =>
        apiFetch<Source>(`/v1/admin/sources/${id}`, token, {
          method: 'PATCH',
          body: JSON.stringify(data),
        }),
      delete: (id: string) =>
        apiFetch<void>(`/v1/admin/sources/${id}`, token, { method: 'DELETE' }),
    },
    auditLog: {
      list: (params?: { page?: number; page_size?: number; resource_type?: string }) =>
        apiFetch<{ items: AuditLogEntry[]; total: number }>(
          '/v1/admin/audit-log',
          token,
          undefined,
          params as Record<string, string | number | boolean | undefined>,
        ),
    },
  }
}
