"use client";

import { useState } from "react";
import { ChevronRight, User, Volume2, Bell, Info } from "lucide-react";
import Link from "next/link";

import { RevokeAccountModal } from "@/components/revoke-account-modal";
import { cn } from "@/lib/utils";

interface SettingsRowProps {
  icon: React.ElementType;
  label: string;
  description?: string;
  href?: string;
  onClick?: () => void;
  destructive?: boolean;
}

function SettingsRow({
  icon: Icon,
  label,
  description,
  href,
  onClick,
  destructive,
}: SettingsRowProps) {
  const content = (
    <div
      className={cn(
        "flex items-center gap-3 rounded-2xl px-4 py-3.5 transition-colors",
        "hover:bg-[color:var(--surface-elevated)]/80 active:bg-[color:var(--surface-elevated)]/60",
        destructive && "hover:bg-[color:var(--error)]/10",
      )}
    >
      <Icon
        className={cn(
          "h-5 w-5 shrink-0",
          destructive
            ? "text-[color:var(--error)]"
            : "text-[color:var(--text-secondary)]",
        )}
        strokeWidth={1.5}
      />
      <div className="min-w-0 flex-1">
        <span
          className={cn(
            "block text-sm font-medium",
            destructive
              ? "text-[color:var(--error)]"
              : "text-[color:var(--text-primary)]",
          )}
        >
          {label}
        </span>
        {description && (
          <p className="mt-0.5 text-xs text-[color:var(--text-tertiary)]">
            {description}
          </p>
        )}
      </div>
      <ChevronRight className="h-4 w-4 shrink-0 text-[color:var(--text-tertiary)]" />
    </div>
  );

  if (href) {
    return <Link href={href}>{content}</Link>;
  }

  return (
    <button type="button" onClick={onClick} className="w-full text-left">
      {content}
    </button>
  );
}

export default function SettingsPage() {
  const [revokeOpen, setRevokeOpen] = useState(false);

  return (
    <div className="relative flex min-h-screen flex-col">
      <header
        className="glass-frost sticky top-0 z-10 px-5 pb-4"
        style={{ paddingTop: "max(2rem, calc(env(safe-area-inset-top) + 2rem))" }}
      >
        <h1 className="font-[family-name:var(--font-display)] text-[30px] italic leading-none tracking-[-0.01em] text-[color:var(--text-primary)]">
          Definições
        </h1>
      </header>

      <section className="flex-1 space-y-1 px-4 py-4">
        <div className="mb-3 mt-2">
          <h2 className="px-4 text-[10px] font-semibold uppercase tracking-[0.22em] text-[color:var(--text-tertiary)]">
            Conta
          </h2>
        </div>
        <SettingsRow
          icon={User}
          label="Conta Google"
          description="Gerir ligação e permissões"
          href="/settings/account"
        />

        <div className="mb-3 mt-8">
          <h2 className="px-4 text-[10px] font-semibold uppercase tracking-[0.22em] text-[color:var(--text-tertiary)]">
            Vox
          </h2>
        </div>
        <SettingsRow
          icon={Volume2}
          label="Voz e áudio"
          description="Sensibilidade auto-silêncio, idioma"
        />
        <SettingsRow
          icon={Bell}
          label="Notificações"
          description="Quando o Vox te deve avisar"
        />

        <div className="mb-3 mt-8">
          <h2 className="px-4 text-[10px] font-semibold uppercase tracking-[0.22em] text-[color:var(--text-tertiary)]">
            Sobre
          </h2>
        </div>
        <SettingsRow
          icon={Info}
          label="Sobre o Per4Biz"
          description="Versão, privacidade, licenças"
        />
      </section>

      <RevokeAccountModal open={revokeOpen} onOpenChange={setRevokeOpen} />
    </div>
  );
}
