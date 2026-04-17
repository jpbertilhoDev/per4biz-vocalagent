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
      <div className="relative flex min-h-screen flex-col">
        <header
          className="glass-frost sticky top-0 z-10 px-5 pb-4"
          style={{ paddingTop: "max(2rem, calc(env(safe-area-inset-top) + 2rem))" }}
        >
          <h1 className="font-[family-name:var(--font-display)] text-[30px] italic leading-none tracking-[-0.01em] text-[color:var(--text-primary)]">
            Inbox
          </h1>
          {!isLoading && !isError && emails.length > 0 && (
            <p className="mt-1.5 text-[10px] uppercase tracking-[0.22em] text-[color:var(--text-tertiary)]">
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
              className="mx-4 mt-8 rounded-2xl border border-[color:var(--error)]/25 bg-[color:var(--error)]/10 p-4 text-sm text-[color:var(--error)]"
            >
              <p className="mb-3">Não foi possível carregar os emails.</p>
              <Button variant="destructive" size="sm" onClick={() => refetch()}>
                Tentar novamente
              </Button>
            </div>
          )}

          {!isLoading && !isError && emails.length === 0 && (
            <div className="flex flex-1 flex-col items-center justify-center px-6 py-24 text-center">
              <p className="max-w-[280px] font-[family-name:var(--font-display)] text-[30px] italic leading-[1.15] text-[color:var(--text-primary)]">
                Sem emails. Só silêncio.
              </p>
              <p className="mt-4 max-w-[260px] text-sm leading-relaxed text-[color:var(--text-secondary)]">
                A caixa está vazia. Volta depois ou pede ao Vox para te avisar.
              </p>
            </div>
          )}

          {!isLoading && !isError && emails.length > 0 && (
            <ul className="divide-y-0">
              {emails.map((email, index) => (
                <li
                  key={email.id}
                  className="animate-fade-in-up"
                  style={{ animationDelay: `${Math.min(index, 10) * 40}ms` }}
                >
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
