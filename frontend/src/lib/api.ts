import { Analytics, AuditEvent, ClarificationRequest, Deal, MerchantPolicy, Product } from "../types/commerce";

export const API_BASE = process.env.NEXT_PUBLIC_ASC_API_URL || "/backend-api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    cache: "no-store",
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new Error(detail?.detail || `Request failed (${response.status})`);
  }
  return response.json();
}

export const api = {
  health: () => request<{ status: string; agent_provider: string; agent_model?: string | null; agent_configured: boolean }>("/api/health"),
  createDeal: (prompt: string) =>
    request<Deal | ClarificationRequest>("/api/deals", { method: "POST", body: JSON.stringify({ prompt }) }),
  listDeals: () => request<{ deals: Deal[] }>("/api/deals"),
  getDeal: (id: string) => request<Deal>(`/api/deals/${id}`),
  rejectDeal: (id: string, reason?: string) => request<Deal>(`/api/deals/${id}/reject`, { method: "POST", body: JSON.stringify({ reason: reason || null }) }),
  acceptDeal: (id: string) =>
    request<{ deal: Deal; order: Record<string, unknown> }>(`/api/deals/${id}/accept`, { method: "POST" }),
  analytics: () => request<Analytics>("/api/analytics"),
  catalog: () => request<{ products: Product[] }>("/api/catalog"),
  policy: () => request<MerchantPolicy>("/api/merchant-policy"),
  updatePolicy: (policy: Partial<MerchantPolicy>) =>
    request<MerchantPolicy>("/api/merchant-policy", { method: "PUT", body: JSON.stringify(policy) }),
  activity: (limit = 100) => request<{ events: AuditEvent[] }>(`/api/audit/recent?limit=${limit}`),
};
