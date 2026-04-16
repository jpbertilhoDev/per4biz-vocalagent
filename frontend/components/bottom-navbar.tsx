"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
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
      className="glass-frost fixed right-0 bottom-0 left-0 z-50 border-t border-divider/50"
    >
      <ul
        className="mx-auto flex h-16 max-w-lg items-center justify-around px-2"
        style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
      >
        {tabs.map((tab) => {
          const isActive =
            pathname === tab.href ||
            (tab.href !== "/chat" && pathname.startsWith(tab.href));
          const Icon = tab.icon;

          return (
            <li key={tab.href}>
              <Link
                href={tab.href}
                aria-label={tab.label}
                aria-current={isActive ? "page" : undefined}
                className={cn(
                  "flex flex-col items-center gap-1 rounded-2xl px-4 py-2 transition-all duration-200",
                  isActive
                    ? "bg-primary/10 text-primary"
                    : "text-text-tertiary hover:text-text-secondary",
                )}
              >
                <Icon className="h-5 w-5" strokeWidth={isActive ? 2.2 : 1.5} />
                <span
                  className={cn(
                    "text-[10px] leading-none",
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
