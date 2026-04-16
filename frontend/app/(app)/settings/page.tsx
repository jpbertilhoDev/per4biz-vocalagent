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
        "flex items-center gap-3 rounded-xl px-4 py-3 transition-colors",
        "hover:bg-surface-elevated active:bg-surface-elevated/80",
        destructive && "hover:bg-error/10",
      )}
    >
      <Icon
        className={cn(
          "h-5 w-5 shrink-0",
          destructive ? "text-error" : "text-text-secondary",
        )}
        strokeWidth={1.5}
      />
      <div className="min-w-0 flex-1">
        <span
          className={cn(
            "text-sm font-medium",
            destructive ? "text-error" : "text-text-primary",
          )}
        >
          {label}
        </span>
        {description && (
          <p className="text-xs text-text-tertiary">{description}</p>
        )}
      </div>
      <ChevronRight className="h-4 w-4 shrink-0 text-text-tertiary" />
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
    <div className="flex min-h-screen flex-col bg-background">
      <header
        className="glass-frost sticky top-0 z-10 border-b border-divider px-4 py-4"
        style={{ paddingTop: "max(1rem, env(safe-area-inset-top))" }}
      >
        <h1 className="text-2xl font-bold tracking-tight text-text-primary">
          Definições
        </h1>
      </header>

      <section className="flex-1 space-y-1 p-4">
        <div className="mb-3">
          <h2 className="px-4 text-xs font-semibold uppercase tracking-wider text-text-tertiary">
            Conta
          </h2>
        </div>
        <SettingsRow
          icon={User}
          label="Conta Google"
          description="Gerir ligação e permissões"
          href="/settings/account"
        />

        <div className="mb-3 mt-6">
          <h2 className="px-4 text-xs font-semibold uppercase tracking-wider text-text-tertiary">
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

        <div className="mb-3 mt-6">
          <h2 className="px-4 text-xs font-semibold uppercase tracking-wider text-text-tertiary">
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
