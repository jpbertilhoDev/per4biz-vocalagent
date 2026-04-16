"use client";

import { useRouter } from "next/navigation";

import { formatRelativeTime } from "@/lib/relative-time";
import { cn } from "@/lib/utils";
import type { EmailListItem } from "@/lib/queries";

export interface EmailItemProps {
  email: EmailListItem;
}

export function EmailItem({ email }: EmailItemProps) {
  const router = useRouter();
  const displayName = email.from_name ?? email.from_email.split("@")[0];
  const initial = (displayName[0] ?? "?").toUpperCase();

  return (
    <button
      type="button"
      data-testid="email-item"
      onClick={() => router.push(`/email/${email.id}`)}
      className={cn(
        "flex w-full items-start gap-3 border-b border-neutral-200 px-4 py-3 text-left transition-colors",
        "hover:bg-neutral-50 active:bg-neutral-100",
        "dark:border-neutral-800 dark:hover:bg-neutral-900 dark:active:bg-neutral-800",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0A84FF]",
      )}
      aria-label={`${displayName}: ${email.subject}${email.is_unread ? " (não lido)" : ""}`}
    >
      {/* Avatar */}
      <div
        aria-hidden
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-neutral-200 font-semibold text-neutral-700 dark:bg-neutral-700 dark:text-neutral-200"
      >
        {initial}
      </div>

      {/* Content */}
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline justify-between gap-2">
          <span
            className={cn(
              "truncate text-sm",
              email.is_unread ? "font-semibold" : "font-normal",
            )}
          >
            {displayName}
          </span>
          <span className="shrink-0 text-xs text-neutral-500">
            {formatRelativeTime(email.received_at)}
          </span>
        </div>
        <div
          className={cn(
            "truncate text-sm",
            email.is_unread
              ? "font-semibold"
              : "text-neutral-800 dark:text-neutral-200",
          )}
        >
          {email.subject || "(sem assunto)"}
        </div>
        <div className="truncate text-xs text-neutral-500">{email.snippet}</div>
      </div>

      {/* Unread dot */}
      {email.is_unread && (
        <div
          data-testid="unread-dot"
          aria-hidden
          className="mt-2 h-2 w-2 shrink-0 rounded-full bg-[#0A84FF]"
        />
      )}
    </button>
  );
}

export default EmailItem;
