/**
 * Placeholder row shown while the inbox query is pending.
 * Rendered ≥3 times by <InboxPage> during loading.
 */
export function EmailSkeleton() {
  return (
    <div
      data-testid="email-skeleton"
      className="flex items-start gap-3 border-b border-divider px-4 py-3"
      aria-hidden
    >
      <div className="h-10 w-1 shrink-0 animate-pulse rounded-full bg-surface-elevated" />
      <div className="h-10 w-10 shrink-0 animate-pulse rounded-full bg-surface-elevated" />
      <div className="flex-1 space-y-2">
        <div className="h-3 w-1/3 animate-pulse rounded bg-surface-elevated" />
        <div className="h-3 w-2/3 animate-pulse rounded bg-surface-elevated" />
        <div className="h-3 w-1/2 animate-pulse rounded bg-surface-elevated" />
      </div>
    </div>
  );
}

export default EmailSkeleton;
