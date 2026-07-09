import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Airflow Observer",
  description: "Prioritized Airflow fixes for small data teams"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen">
          <header className="border-b border-border bg-white">
            <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4">
              <Link href="/" className="text-lg font-semibold tracking-tight">
                Airflow Observer
              </Link>
              <nav className="flex items-center gap-4 text-sm text-muted">
                <Link className="hover:text-ink" href="/">
                  Overview
                </Link>
                <Link className="hover:text-ink" href="/incidents">
                  Incidents
                </Link>
                <Link className="hover:text-ink" href="/recommendations">
                  Recommendations
                </Link>
                <Link className="hover:text-ink" href="/alerts">
                  Alerts
                </Link>
                <Link className="hover:text-ink" href="/onboarding">
                  Onboarding
                </Link>
              </nav>
            </div>
          </header>
          <main className="mx-auto max-w-7xl px-5 py-6">{children}</main>
        </div>
      </body>
    </html>
  );
}
