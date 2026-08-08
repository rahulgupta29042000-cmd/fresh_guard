import type { Metadata } from "next";
import "./globals.css";
import NavBar from "@/components/NavBar";
import { RoleProvider } from "@/lib/role";

export const metadata: Metadata = {
  title: "Fresh_Guard — Quality Risk Intelligence",
  description: "AI-powered quality-risk prediction and visual inspection for quick-commerce fulfillment (MVP prototype)",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <RoleProvider>
          <div className="min-h-screen flex flex-col">
            <NavBar />
            <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6">{children}</main>
            <footer className="text-center text-xs text-[#5b6480] py-4">
              Fresh_Guard MVP prototype — demo/simulated data. Not a production quality-control system.
            </footer>
          </div>
        </RoleProvider>
      </body>
    </html>
  );
}
