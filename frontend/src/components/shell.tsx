"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { clearTokens } from "@/lib/api";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/", label: "Overview" },
  { href: "/lab", label: "Lab" },
  { href: "/allocator", label: "Allocator" },
  { href: "/screener", label: "Screener" },
  { href: "/market", label: "Market" },
  { href: "/backtests", label: "Backtests" },
  { href: "/journal", label: "Journal" },
];

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();

  return (
    <div className="min-h-screen bg-ink-950">
      <header className="sticky top-0 z-20 border-b border-line bg-ink-950/90 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-6">
          <div className="flex items-center gap-8">
            <Link href="/" className="font-mono text-sm tracking-[0.18em] text-warn">
              ALPHAFORGE
            </Link>
            <nav className="flex gap-1">
              {NAV.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "rounded px-3 py-1.5 text-sm text-mute hover:text-white",
                    pathname === item.href && "bg-ink-700 text-white",
                  )}
                >
                  {item.label}
                </Link>
              ))}
            </nav>
          </div>
          <button
            className="text-xs text-mute hover:text-white"
            onClick={() => {
              clearTokens();
              router.push("/login");
            }}
          >
            Sign out
          </button>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-6 py-6">{children}</main>
    </div>
  );
}
