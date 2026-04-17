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

const typeConfig: Record<CardType, { icon: React.ElementType; accent: string; label: string }> = {
  "email-read": { icon: Mail, accent: "text-primary", label: "Email" },
  transcription: { icon: Mic, accent: "text-voice", label: "Voz" },
  draft: { icon: FileText, accent: "text-primary", label: "Draft" },
  confirmation: { icon: CheckCircle2, accent: "text-success", label: "Enviado" },
  error: { icon: AlertCircle, accent: "text-error", label: "Erro" },
  "agenda-placeholder": { icon: Calendar, accent: "text-primary", label: "Vox" },
  "calendar-event": { icon: Calendar, accent: "text-primary", label: "Agenda" },
  "calendar-create": { icon: CalendarPlus, accent: "text-success", label: "Criado" },
  "calendar-confirm": { icon: CalendarCheck, accent: "text-voice", label: "Confirmar" },
  "email-confirm": { icon: Mail, accent: "text-voice", label: "Confirmar" },
  "contact-card": { icon: Users, accent: "text-primary", label: "Contacto" },
};

export interface VoxCardProps {
  card: VoxCardType;
  onAction?: (action: string, cardId: string) => void;
}

export function VoxCard({ card, onAction }: VoxCardProps) {
  const config = typeConfig[card.type];
  const Icon = config.icon;

  return (
    <div
      className={cn(
        "animate-fade-in-up rounded-3xl border border-divider/60 bg-surface-elevated/60 p-5",
        "backdrop-blur-[24px]",
        "shadow-[0_2px_16px_rgba(0,0,0,0.2)]",
        card.type === "confirmation" && "border-success/30",
        card.type === "error" && "border-error/30",
        card.type === "draft" && "border-primary/20",
        card.type === "calendar-event" && "border-primary/20",
        card.type === "calendar-create" && "border-success/30",
        card.type === "calendar-confirm" && "border-voice/30",
        card.type === "email-confirm" && "border-voice/30",
        card.type === "contact-card" && "border-primary/20",
      )}
      role="article"
      aria-label={`${config.label}: ${card.title}`}
    >
      <div className="mb-3 flex items-center gap-2.5">
        <div
          className={cn(
            "flex h-7 w-7 items-center justify-center rounded-lg",
            card.type === "confirmation" && "bg-success/15",
            card.type === "error" && "bg-error/15",
            card.type === "draft" && "bg-primary/15",
            card.type === "email-read" && "bg-primary/15",
            card.type === "transcription" && "bg-voice/15",
            card.type === "agenda-placeholder" && "bg-primary/15",
            card.type === "calendar-event" && "bg-primary/15",
            card.type === "calendar-create" && "bg-success/15",
            card.type === "calendar-confirm" && "bg-voice/15",
            card.type === "email-confirm" && "bg-voice/15",
            card.type === "contact-card" && "bg-primary/15",
          )}
        >
          <Icon className={cn("h-3.5 w-3.5", config.accent)} strokeWidth={2} />
        </div>
        <span className={cn("text-[11px] font-semibold uppercase tracking-widest", config.accent)}>
          {config.label}
        </span>
        <span className="ml-auto text-[10px] text-text-tertiary tabular-nums">
          {new Date(card.createdAt).toLocaleTimeString("pt-PT", {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </span>
      </div>

      <h3 className="mb-1.5 text-[15px] font-semibold text-text-primary leading-snug">
        {card.title}
      </h3>

      <p className="mb-4 text-sm leading-relaxed text-text-secondary whitespace-pre-wrap">
        {card.content}
      </p>

      {card.meta && Object.keys(card.meta).length > 0 && (
        <div className="mb-4 space-y-1.5 rounded-2xl bg-surface/80 p-3">
          {Object.entries(card.meta).map(([key, value]) => (
            <div key={key} className="flex items-center justify-between text-xs">
              <span className="text-text-tertiary">{key}</span>
              <span className="font-medium text-text-primary">{value}</span>
            </div>
          ))}
        </div>
      )}

      {card.actions && card.actions.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {card.actions.map((action, i) => (
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
                action.action === "tts" && "text-voice hover:text-voice hover:bg-voice/10",
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
