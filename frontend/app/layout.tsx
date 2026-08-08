import type { Metadata } from "next";
import "./globals.css";
import NavBar from "@/components/NavBar";

export const metadata: Metadata = {
  title: "Fresh_Guard — Quality Risk Intelligence",
  description: "AI-powered quality-risk prediction for quick-commerce fulfillment (Phase 1 prototype)",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen flex flex-col">
          <NavBar />
          <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6">{children}</main>
          <footer className="text-center text-xs text-[#5b6480] py-4">
            Fresh_Guard Phase 1 — prototype, synthetic data. Not a production damage-prediction system.
          </footer>
        </div>
      </body>
    </html>
  );
}
