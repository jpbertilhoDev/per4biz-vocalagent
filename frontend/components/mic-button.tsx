"use client";

import { Mic, MicOff, Loader2, Volume2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { MicState } from "@/lib/chat-store";

export interface MicButtonProps {
  state: MicState;
  onClick: () => void;
  disabled?: boolean;
}

const stateConfig: Record<
  MicState,
  { icon: React.ElementType; bg: string; ring: string; label: string; extra?: string }
> = {
  idle: {
    icon: Mic,
    bg: "bg-[color:var(--primary)] text-white",
    ring: "shadow-[0_0_32px_rgba(108,92,231,0.35)]",
    label: "Toca para falar",
    extra: "mic-aurora",
  },
  listening: {
    icon: Mic,
    bg: "bg-[color:var(--voice)] text-white",
    ring: "shadow-[0_0_40px_rgba(0,206,255,0.55)] animate-pulse-glow",
    label: "A ouvir…",
  },
  "silence-detected": {
    icon: Mic,
    bg: "bg-[color:var(--primary)]/80 text-white",
    ring: "shadow-[0_0_20px_rgba(108,92,231,0.35)]",
    label: "A processar…",
  },
  processing: {
    icon: Loader2,
    bg: "bg-[color:var(--primary)]/80 text-white",
    ring: "shadow-[0_0_20px_rgba(108,92,231,0.35)]",
    label: "Vox a pensar…",
  },
  speaking: {
    icon: Volume2,
    bg: "bg-[color:var(--voice)]/85 text-white",
    ring: "shadow-[0_0_32px_rgba(0,206,255,0.45)] animate-pulse-glow",
    label: "Vox a falar…",
  },
  error: {
    icon: MicOff,
    bg: "bg-[color:var(--error)]/85 text-white",
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
          "flex h-16 w-16 items-center justify-center rounded-full",
          "transition-[transform,box-shadow,background-color] duration-300 ease-[cubic-bezier(0.32,0.72,0,1)]",
          config.bg,
          config.ring,
          config.extra,
          "hover:scale-[1.04] active:scale-[0.96]",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--primary)]/50 focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--bg-base)]",
          disabled && "pointer-events-none opacity-40",
        )}
      >
        <Icon
          className={cn("h-7 w-7", state === "processing" && "animate-spin")}
          strokeWidth={1.8}
        />
      </button>
      <span className="text-[11px] font-medium tracking-[0.02em] text-[color:var(--text-tertiary)]">
        {config.label}
      </span>
    </div>
  );
}
