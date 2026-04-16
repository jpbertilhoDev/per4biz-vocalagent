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
        "flex w-full items-start gap-3.5 px-5 py-4 text-left transition-all duration-150",
        "hover:bg-surface active:bg-surface-elevated",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-inset",
      )}
      aria-label={`${displayName}: ${email.subject}${email.is_unread ? " (não lido)" : ""}`}
    >
      <div
        aria-hidden
        className={cn(
          "mt-0.5 h-10 w-1 shrink-0 rounded-full",
          email.is_unread ? "bg-primary" : "bg-divider",
        )}
      />

      <div
        aria-hidden
        className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-surface-elevated text-sm font-semibold text-text-secondary ring-1 ring-divider/60"
      >
        {initial}
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex items-baseline justify-between gap-2">
          <span
            className={cn(
              "truncate text-sm",
              email.is_unread
                ? "font-semibold text-text-primary"
                : "font-normal text-text-secondary",
            )}
          >
            {displayName}
          </span>
          <span className="shrink-0 text-[11px] tabular-nums text-text-tertiary">
            {formatRelativeTime(email.received_at)}
          </span>
        </div>
        <div
          className={cn(
            "truncate text-sm",
            email.is_unread
              ? "font-semibold text-text-primary"
              : "text-text-secondary",
          )}
        >
          {email.subject || "(sem assunto)"}
        </div>
        <div className="mt-0.5 truncate text-xs text-text-tertiary">
          {email.snippet}
        </div>
      </div>

      {email.is_unread && (
        <div
          data-testid="unread-dot"
          aria-hidden
          className="mt-2 h-2.5 w-2.5 shrink-0 rounded-full bg-voice shadow-[0_0_8px_rgba(0,206,255,0.4)]"
        />
      )}
    </button>
  );
}

export default EmailItem;
