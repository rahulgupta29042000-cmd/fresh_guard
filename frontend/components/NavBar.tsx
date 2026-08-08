"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ROLE_CONFIG, Role, useRole } from "@/lib/role";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const ALL_LINKS: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/orders": "Orders",
  "/analytics": "Analytics",
  "/inspections": "Inspections",
  "/picker": "Picker",
  "/qc/review": "QC Review",
};

export default function NavBar() {
  const pathname = usePathname();
  const router = useRouter();
  const { role, setRole } = useRole();
  const [menuOpen, setMenuOpen] = useState(false);
  const [demoMode, setDemoMode] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/api/health`)
      .then((r) => r.json())
      .then((d) => setDemoMode(!!d.demoMode))
      .catch(() => {});
  }, []);

  const orderedLinks = ROLE_CONFIG[role].navOrder;

  function switchRole(r: Role) {
    setRole(r);
    setMenuOpen(false);
    router.push(ROLE_CONFIG[r].home);
  }

  return (
    <header className="border-b border-[#232b40] bg-[#0c101a]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
        <Link href={ROLE_CONFIG[role].home} className="flex items-center gap-2 font-semibold text-lg shrink-0">
          <span className="text-xl">🛡️</span>
          <span>
            Fresh<span className="text-[#4f7cff]">_Guard</span>
          </span>
          {demoMode && (
            <span className="badge bg-[#4f7cff]/15 text-[#4f7cff] text-[10px]" title="Seeded data + simulation vision — see README">
              Demo Mode
            </span>
          )}
        </Link>
        <nav className="flex items-center gap-1 overflow-x-auto">
          {orderedLinks.map((href) => {
            const active = pathname === href || (href !== "/" && pathname?.startsWith(href));
            return (
              <Link
                key={href}
                href={href}
                className={`px-3 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${
                  active ? "bg-[#1a2136] text-white" : "text-[#9aa2ba] hover:text-white"
                }`}
              >
                {ALL_LINKS[href]}
              </Link>
            );
          })}
        </nav>
        <div className="relative shrink-0">
          <button
            className="btn btn-secondary text-xs"
            onClick={() => setMenuOpen((o) => !o)}
            aria-haspopup="true"
            aria-expanded={menuOpen}
          >
            {ROLE_CONFIG[role].label} ▾
          </button>
          {menuOpen && (
            <div className="absolute right-0 mt-2 w-52 card p-1 z-10">
              {(Object.keys(ROLE_CONFIG) as Role[]).map((r) => (
                <button
                  key={r}
                  onClick={() => switchRole(r)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm ${
                    r === role ? "bg-[#1a2136] text-white" : "text-[#9aa2ba] hover:bg-[#1a2136] hover:text-white"
                  }`}
                >
                  {ROLE_CONFIG[r].label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
