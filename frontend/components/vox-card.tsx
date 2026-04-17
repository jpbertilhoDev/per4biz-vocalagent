"use client";

import {
  Mail,
  Mic,
  FileText,
  CheckCircle2,
  AlertCircle,
  Calendar,
  Users,
  CalendarPlus,
  CalendarCheck,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { VoxCard as VoxCardType, VoxCardType as CardType } from "@/lib/chat-store";
import { Button } from "@/components/ui/button";

const typeConfig: Record<
  CardType,
  { icon: React.ElementType; accent: string; label: string }
> = {
  "email-read": { icon: Mail, accent: "text-[color:var(--primary)]", label: "Email" },
  transcription: { icon: Mic, accent: "text-[color:var(--voice)]", label: "Voz" },
  draft: { icon: FileText, accent: "text-[color:var(--primary)]", label: "Draft" },
  confirmation: { icon: CheckCircle2, accent: "text-success", label: "Enviado" },
  error: { icon: AlertCircle, accent: "text-[color:var(--error)]", label: "Erro" },
  "agenda-placeholder": { icon: Calendar, accent: "text-[color:var(--primary)]", label: "Vox" },
  "calendar-event": { icon: Calendar, accent: "text-[color:var(--primary)]", label: "Agenda" },
  "calendar-create": { icon: CalendarPlus, accent: "text-success", label: "Criado" },
  "calendar-confirm": { icon: CalendarCheck, accent: "text-[color:var(--voice)]", label: "Confirmar" },
  "email-confirm": { icon: Mail, accent: "text-[color:var(--voice)]", label: "Confirmar" },
  "contact-card": { icon: Users, accent: "text-[color:var(--primary)]", label: "Contacto" },
};

export interface VoxCardProps {
  card: VoxCardType;
  onAction?: (action: string, cardId: string) => void;
}

export function VoxCard({ card, onAction }: VoxCardProps) {
  const config = typeConfig[card.type];
  const Icon = config.icon;
  const isHero = card.type === "agenda-placeholder";
  const titleClass = isHero
    ? "font-[family-name:var(--font-display)] italic text-[26px] leading-[1.15] tracking-[-0.01em] text-[color:var(--text-primary)]"
    : "text-[15px] font-semibold leading-snug text-[color:var(--text-primary)]";

  return (
    <div
      className={cn(
        "animate-fade-in-up rounded-3xl backdrop-blur-xl",
        "border shadow-[0_2px_16px_rgba(0,0,0,0.2)]",
        isHero ? "p-6" : "p-5",
        // Base hairline surface
        "border-[color:var(--hairline)]",
        "bg-[linear-gradient(180deg,rgba(245,243,237,0.035)_0%,rgba(245,243,237,0.015)_100%)]",
        // Type-specific hairline tints (replace prior heavy rings)
        card.type === "confirmation" && "border-success/20",
        card.type === "error" && "border-[color:var(--error)]/25",
        card.type === "draft" && "border-[color:var(--primary)]/18",
        card.type === "calendar-event" && "border-[color:var(--primary)]/18",
        card.type === "calendar-create" && "border-success/20",
        card.type === "calendar-confirm" && "border-[color:var(--voice)]/22",
        card.type === "email-confirm" && "border-[color:var(--voice)]/22",
        card.type === "contact-card" && "border-[color:var(--primary)]/18",
      )}
      role="article"
      aria-label={`${config.label}: ${card.title}`}
    >
      <div className="mb-3 flex items-center gap-2.5">
        <div
          className={cn(
            "flex h-7 w-7 items-center justify-center rounded-lg",
            card.type === "confirmation" && "bg-success/15",
            card.type === "error" && "bg-[color:var(--error)]/15",
            card.type === "draft" && "bg-[color:var(--primary)]/15",
            card.type === "email-read" && "bg-[color:var(--primary)]/15",
            card.type === "transcription" && "bg-[color:var(--voice)]/15",
            card.type === "agenda-placeholder" && "bg-[color:var(--primary)]/15",
            card.type === "calendar-event" && "bg-[color:var(--primary)]/15",
            card.type === "calendar-create" && "bg-success/15",
            card.type === "calendar-confirm" && "bg-[color:var(--voice)]/15",
            card.type === "email-confirm" && "bg-[color:var(--voice)]/15",
            card.type === "contact-card" && "bg-[color:var(--primary)]/15",
          )}
        >
          <Icon className={cn("h-3.5 w-3.5", config.accent)} strokeWidth={2} />
        </div>
        <span
          className={cn(
            "text-[10px] font-semibold uppercase tracking-[0.22em]",
            config.accent,
          )}
        >
          {config.label}
        </span>
        <span className="ml-auto text-[10px] tabular-nums text-[color:var(--text-tertiary)]">
          {new Date(card.createdAt).toLocaleTimeString("pt-PT", {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </span>
      </div>

      <h3 className={cn("mb-2", titleClass)}>{card.title}</h3>

      <p
        className={cn(
          "mb-4 whitespace-pre-wrap leading-relaxed text-[color:var(--text-secondary)]",
          isHero ? "text-[14px]" : "text-sm",
        )}
      >
        {card.content}
      </p>

      {card.meta && Object.keys(card.meta).length > 0 && (
        <div className="mb-4 space-y-1.5 rounded-2xl border border-[color:var(--hairline)] bg-[color:var(--surface-elevated)]/60 p-3">
          {Object.entries(card.meta)
            .filter(([key]) => key !== "pendingId")
            .map(([key, value]) => (
              <div
                key={key}
                className="flex items-center justify-between text-xs"
              >
                <span className="uppercase tracking-[0.14em] text-[10px] text-[color:var(--text-tertiary)]">
                  {key}
                </span>
                <span className="font-medium text-[color:var(--text-primary)]">
                  {value}
                </span>
              </div>
            ))}
        </div>
      )}

      {card.actions && card.actions.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {card.actions.map((action) => (
            <Button
              key={action.action}
              size="sm"
              variant={
                action.action === "send" ||
                action.action === "confirm" ||
                action.action === "calendar-create-confirm" ||
                action.action === "calendar-edit-confirm" ||
                action.action === "calendar-delete-confirm" ||
                action.action === "email-delete-confirm"
                  ? "default"
                  : "ghost"
              }
              onClick={() => onAction?.(action.action, card.id)}
              className={cn(
                "rounded-2xl text-xs font-medium",
                action.action === "tts" &&
                  "text-[color:var(--voice)] hover:bg-[color:var(--voice)]/10 hover:text-[color:var(--voice)]",
              )}
            >
              {action.label}
            </Button>
          ))}
        </div>
      )}
    </div>
  );
}
