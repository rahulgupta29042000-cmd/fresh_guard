"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { ROLE_CONFIG, Role } from "@/lib/role";

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    const stored = window.localStorage.getItem("freshguard_role") as Role | null;
    const home = stored && ROLE_CONFIG[stored] ? ROLE_CONFIG[stored].home : "/dashboard";
    router.replace(home);
  }, [router]);

  return null;
}
