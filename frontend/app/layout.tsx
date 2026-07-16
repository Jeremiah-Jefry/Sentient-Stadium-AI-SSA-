/**
 * Root layout for the StadiumMind OS frontend.
 *
 * Wraps the entire application with the AuthProvider and
 * provides global styles and metadata.
 */

import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "@/app/globals.css";
import { AuthProvider } from "@/contexts/auth-context";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "StadiumMind OS - Volunteer Platform",
  description:
    "Enterprise-grade Multi-Agent Stadium Intelligence Platform for FIFA World Cup 2026",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} font-sans antialiased`}>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
