import { apiFetch } from "./api";

// ---------------------------------------------------------------------------
// Email types + queries
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Calendar types + queries
// ---------------------------------------------------------------------------

export interface CalendarEvent {
  id: string;
  summary: string;
  description: string;
  location: string;
  start: string;
  end: string;
  is_all_day: boolean;
  attendees: { email: string; name: string; response_status: string }[];
  status: string;
  html_link: string;
}

export interface CalendarListResponse {
  events: CalendarEvent[];
  count: number;
}

export const calendarKeys = {
  all: ["calendar"] as const,
  events: (timeMin?: string, timeMax?: string) =>
    [...calendarKeys.all, "events", { timeMin, timeMax }] as const,
  detail: (id: string) => [...calendarKeys.all, "detail", id] as const,
};

export function listCalendarEvents(
  timeMin?: string,
  timeMax?: string,
  maxResults = 25
): Promise<CalendarListResponse> {
  const params = new URLSearchParams();
  if (timeMin) params.set("time_min", timeMin);
  if (timeMax) params.set("time_max", timeMax);
  params.set("max_results", String(maxResults));
  const query = params.toString();
  return apiFetch<CalendarListResponse>(`/calendar/events${query ? `?${query}` : ""}`);
}

export function getCalendarEvent(eventId: string): Promise<CalendarEvent> {
  return apiFetch<CalendarEvent>(`/calendar/events/${encodeURIComponent(eventId)}`);
}

export interface CreateEventPayload {
  summary: string;
  start: string;
  end: string;
  description?: string;
  location?: string;
}

export function createCalendarEvent(payload: CreateEventPayload): Promise<CalendarEvent> {
  return apiFetch<CalendarEvent>("/calendar/events", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export interface UpdateEventPayload {
  summary?: string;
  start?: string;
  end?: string;
  description?: string;
  location?: string;
}

export function updateCalendarEvent(
  eventId: string,
  payload: UpdateEventPayload
): Promise<CalendarEvent> {
  return apiFetch<CalendarEvent>(`/calendar/events/${encodeURIComponent(eventId)}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteCalendarEvent(eventId: string): Promise<{ status: string; event_id: string }> {
  return apiFetch<{ status: string; event_id: string }>(
    `/calendar/events/${encodeURIComponent(eventId)}`,
    { method: "DELETE" }
  );
}

// ---------------------------------------------------------------------------
// Contacts types + queries
// ---------------------------------------------------------------------------

export interface ContactItem {
  resource_name: string;
  display_name: string;
  given_name: string;
  family_name: string;
  emails: string[];
  phones: string[];
  organization: string;
  title: string;
}

export interface ContactsListResponse {
  contacts: ContactItem[];
  count: number;
}

export const contactsKeys = {
  all: ["contacts"] as const,
  search: (query: string) => [...contactsKeys.all, "search", query] as const,
  list: () => [...contactsKeys.all, "list"] as const,
};

export function searchContacts(query: string, maxResults = 20): Promise<ContactsListResponse> {
  const params = new URLSearchParams();
  params.set("query", query);
  params.set("max_results", String(maxResults));
  return apiFetch<ContactsListResponse>(`/contacts/search?${params.toString()}`);
}

export function listContacts(maxResults = 20): Promise<ContactsListResponse> {
  return apiFetch<ContactsListResponse>(`/contacts/list?max_results=${maxResults}`);
}
