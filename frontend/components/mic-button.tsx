"use client";

import { Mic, MicOff, Loader2, Volume2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { MicState } from "@/lib/chat-store";

export interface MicButtonProps {
  state: MicState;
  onClick: () => void;
  disabled?: boolean;
}

const stateConfig: Record<MicState, { icon: React.ElementType; bg: string; ring: string; label: string }> = {
  idle: {
    icon: Mic,
    bg: "bg-primary text-white",
    ring: "shadow-[0_0_24px_rgba(108,92,231,0.3)]",
    label: "Toca para falar",
  },
  listening: {
    icon: Mic,
    bg: "bg-voice text-white",
    ring: "shadow-[0_0_28px_rgba(0,206,255,0.45)] animate-pulse-glow",
    label: "A ouvir…",
  },
  "silence-detected": {
    icon: Mic,
    bg: "bg-primary/80 text-white",
    ring: "shadow-[0_0_16px_rgba(108,92,231,0.3)]",
    label: "A processar…",
  },
  processing: {
    icon: Loader2,
    bg: "bg-primary/80 text-white",
    ring: "shadow-[0_0_16px_rgba(108,92,231,0.3)]",
    label: "Vox a pensar…",
  },
  speaking: {
    icon: Volume2,
    bg: "bg-voice/80 text-white",
    ring: "shadow-[0_0_24px_rgba(0,206,255,0.35)] animate-pulse-glow",
    label: "Vox a falar…",
  },
  error: {
    icon: MicOff,
    bg: "bg-error/80 text-white",
    ring: "",
    label: "Erro — toca para tentar",
  },
};

export function MicButton({ state, onClick, disabled }: MicButtonProps) {
  const config = stateConfig[state];
  const Icon = config.icon;

  return (
    <div className="flex flex-col items-center gap-2.5">
      <button
        type="button"
        onClick={onClick}
        disabled={disabled}
        aria-label={config.label}
        className={cn(
          "flex h-16 w-16 items-center justify-center rounded-full transition-all duration-200",
          config.bg,
          config.ring,
          "hover:scale-105 active:scale-95",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
          disabled && "pointer-events-none opacity-40",
        )}
      >
        <Icon
          className={cn("h-7 w-7", state === "processing" && "animate-spin")}
          strokeWidth={1.8}
        />
      </button>
      <span className="text-[11px] font-medium text-text-tertiary">{config.label}</span>
    </div>
  );
}
