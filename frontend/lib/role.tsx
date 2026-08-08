"use client";

import { createContext, useContext, useEffect, useState } from "react";

export type Role = "ops" | "picker" | "qc";

export const ROLE_CONFIG: Record<Role, { label: string; home: string; navOrder: string[] }> = {
  ops: {
    label: "Operations Manager",
    home: "/dashboard",
    navOrder: ["/dashboard", "/orders", "/analytics", "/inspections", "/picker", "/qc/review"],
  },
  picker: {
    label: "Picker",
    home: "/picker",
    navOrder: ["/picker", "/orders", "/inspections", "/dashboard", "/analytics", "/qc/review"],
  },
  qc: {
    label: "QC Reviewer",
    home: "/qc/review",
    navOrder: ["/qc/review", "/inspections", "/orders", "/dashboard", "/analytics", "/picker"],
  },
};

const STORAGE_KEY = "freshguard_role";

type RoleContextValue = { role: Role; setRole: (r: Role) => void };

const RoleContext = createContext<RoleContextValue>({ role: "ops", setRole: () => {} });

export function RoleProvider({ children }: { children: React.ReactNode }) {
  const [role, setRoleState] = useState<Role>("ops");

  useEffect(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY) as Role | null;
    if (stored && ROLE_CONFIG[stored]) setRoleState(stored);
  }, []);

  function setRole(r: Role) {
    setRoleState(r);
    window.localStorage.setItem(STORAGE_KEY, r);
  }

  return <RoleContext.Provider value={{ role, setRole }}>{children}</RoleContext.Provider>;
}

export function useRole() {
  return useContext(RoleContext);
}
