// Thin typed wrapper around the backend. Every request carries the mock-auth X-User-Id header.

export type User = { id: number; name: string; email: string };
export type DocSummary = { id: number; title: string; owner: User; updated_at: string };
export type Doc = DocSummary & {
  content_html: string;
  created_at: string;
  is_owner: boolean;
  shared_with: User[];
};
export type DocList = { owned: DocSummary[]; shared: DocSummary[] };

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

let currentUserId: number | null = null;
export function setCurrentUser(id: number | null) {
  currentUserId = id;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (currentUserId !== null) headers.set("X-User-Id", String(currentUserId));
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");

  let res: Response;
  try {
    res = await fetch(`/api${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, "Network error: can't reach the server.");
  }
  if (!res.ok) {
    // FastAPI errors are {detail: string} or, for validation errors, {detail: [{msg}]}.
    const body = await res.json().catch(() => null);
    const detail = body?.detail;
    const message = typeof detail === "string" ? detail : detail?.[0]?.msg ?? `Request failed (${res.status})`;
    throw new ApiError(res.status, message);
  }
  return res.json() as Promise<T>;
}

export const api = {
  users: () => request<User[]>("/users"),
  listDocs: () => request<DocList>("/documents"),
  getDoc: (id: number) => request<Doc>(`/documents/${id}`),
  createDoc: () => request<Doc>("/documents", { method: "POST", body: JSON.stringify({}) }),
  updateDoc: (id: number, patch: { title?: string; content_html?: string }) =>
    request<Doc>(`/documents/${id}`, { method: "PATCH", body: JSON.stringify(patch) }),
  importDoc: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<Doc>("/documents/import", { method: "POST", body: form });
  },
  shareDoc: (id: number, email: string) =>
    request<Doc>(`/documents/${id}/shares`, { method: "POST", body: JSON.stringify({ email }) }),
};

// Must match the backend (importers.py). The server is the real check; these give fast feedback.
export const IMPORT_ACCEPT = ".txt,.md,.docx";
export const MAX_IMPORT_BYTES = 2 * 1024 * 1024;
