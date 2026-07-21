import type { Metadata } from "next";
import "./globals.css";
import { StoreProvider } from "@/lib/store";

// Font sistem (bukan next/font/google) supaya build & runtime tidak butuh
// internet — penting untuk jaringan pabrik tertutup.
export const metadata: Metadata = {
  title: "OptiBayer — CRO Console",
  description:
    "Bayer Process Advisor: digital twin neuro-symbolic untuk pabrik alumina",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="id" className="h-full antialiased">
      <body className="min-h-full">
        <StoreProvider>{children}</StoreProvider>
      </body>
    </html>
  );
}
