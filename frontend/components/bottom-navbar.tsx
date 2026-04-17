"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import { MessageCircle, Inbox, Calendar, Settings } from "lucide-react";
import { cn } from "@/lib/utils";

const tabs = [
  { href: "/chat", label: "Chat", icon: MessageCircle },
  { href: "/inbox", label: "Inbox", icon: Inbox },
  { href: "/agenda", label: "Agenda", icon: Calendar },
  { href: "/settings", label: "Definições", icon: Settings },
] as const;

export function BottomNavbar() {
  const pathname = usePathname();

  return (
    <nav
      aria-label="Navegação principal"
      className="fixed inset-x-0 bottom-0 z-50 flex justify-center px-4"
      style={{ paddingBottom: "max(0.75rem, env(safe-area-inset-bottom))" }}
    >
      <ul className="glass-frost mx-auto flex w-full max-w-[22rem] items-center justify-between gap-1 rounded-[28px] px-2 py-2 shadow-[0_8px_32px_rgba(0,0,0,0.45)]">
        {tabs.map((tab) => {
          const isActive =
            pathname === tab.href ||
            (tab.href !== "/chat" && pathname.startsWith(tab.href));
          const Icon = tab.icon;

          return (
            <li key={tab.href} className="flex-1">
              <Link
                href={tab.href}
                aria-label={tab.label}
                aria-current={isActive ? "page" : undefined}
                className={cn(
                  "relative flex flex-col items-center justify-center gap-1 rounded-2xl px-2 py-2 transition-colors duration-200",
                  isActive
                    ? "text-[color:var(--primary)]"
                    : "text-[color:var(--text-tertiary)] hover:text-[color:var(--text-secondary)]",
                )}
              >
                {isActive && (
                  <motion.span
                    layoutId="navbar-indicator"
                    className="absolute inset-0 rounded-2xl"
                    style={{
                      background: "var(--primary-soft)",
                      boxShadow: "inset 0 0 0 1px rgba(108, 92, 231, 0.22)",
                    }}
                    transition={{ type: "spring", stiffness: 420, damping: 34 }}
                  />
                )}
                <Icon
                  className="relative z-10 h-5 w-5"
                  strokeWidth={isActive ? 2.2 : 1.5}
                />
                <span
                  className={cn(
                    "relative z-10 text-[10px] leading-none tracking-[0.02em]",
                    isActive ? "font-semibold" : "font-medium",
                  )}
                >
                  {tab.label}
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
