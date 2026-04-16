import { apiFetch } from "./api";

export interface EmailListItem {
  id: string;
  from_name: string | null;
  from_email: string;
  subject: string;
  snippet: string;
  received_at: string;
  is_unread: boolean;
}

export interface EmailDetail extends EmailListItem {
  to_emails: string[];
  cc_emails: string[];
  body_text: string;
}

export interface EmailListResponse {
  emails: EmailListItem[];
  next_page_token: string | null;
}

export const emailsKeys = {
  all: ["emails"] as const,
  list: (pageToken?: string) => [...emailsKeys.all, "list", { pageToken }] as const,
  detail: (id: string) => [...emailsKeys.all, "detail", id] as const,
};

export function listEmails(pageToken?: string): Promise<EmailListResponse> {
  const params = new URLSearchParams();
  if (pageToken) params.set("page_token", pageToken);
  const query = params.toString();
  return apiFetch<EmailListResponse>(`/emails/list${query ? `?${query}` : ""}`);
}

export function getEmail(id: string): Promise<EmailDetail> {
  return apiFetch<EmailDetail>(`/emails/${encodeURIComponent(id)}`);
}
