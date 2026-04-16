"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";

import { EmailItem } from "@/components/email-item";
import { EmailSkeleton } from "@/components/email-skeleton";
import { PullToRefresh } from "@/components/pull-to-refresh";
import { Button } from "@/components/ui/button";
import { emailsKeys, listEmails } from "@/lib/queries";

export default function InboxPage() {
  const queryClient = useQueryClient();
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: emailsKeys.list(),
    queryFn: () => listEmails(),
  });

  const emails = data?.emails ?? [];
  const unreadCount = emails.filter((e) => e.is_unread).length;

  const handleRefresh = async () => {
    await queryClient.invalidateQueries({ queryKey: emailsKeys.list() });
  };

  return (
    <PullToRefresh onRefresh={handleRefresh}>
      <div className="flex min-h-screen flex-col bg-background">
        <header
          className="glass-frost sticky top-0 z-10 border-b border-divider px-4 py-4"
          style={{ paddingTop: "max(1rem, env(safe-area-inset-top))" }}
        >
          <h1 className="text-2xl font-bold tracking-tight text-text-primary">
            Inbox
          </h1>
          {!isLoading && !isError && emails.length > 0 && (
            <p className="text-xs text-text-tertiary">
              {unreadCount} não {unreadCount === 1 ? "lido" : "lidos"}
            </p>
          )}
        </header>

        <section className="flex-1">
          {isLoading && (
            <>
              <EmailSkeleton />
              <EmailSkeleton />
              <EmailSkeleton />
            </>
          )}

          {isError && (
            <div
              role="alert"
              className="mx-4 mt-8 rounded-xl bg-error/10 p-4 text-sm text-error"
            >
              <p className="mb-3">Não foi possível carregar os emails.</p>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => refetch()}
              >
                Tentar novamente
              </Button>
            </div>
          )}

          {!isLoading && !isError && emails.length === 0 && (
            <div className="flex flex-1 flex-col items-center justify-center py-24 text-center">
              <p className="text-text-tertiary">Sem emails</p>
            </div>
          )}

          {!isLoading && !isError && emails.length > 0 && (
            <ul className="divide-y-0">
              {emails.map((email) => (
                <li key={email.id}>
                  <EmailItem email={email} />
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </PullToRefresh>
  );
}
