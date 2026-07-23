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
  // suppressHydrationWarning: ekstensi browser (mis. Bitdefender `bis_register`,
  // Grammarly, dsb.) menyuntik atribut ke <html>/<body> SEBELUM React hydrate,
  // memicu warning mismatch palsu. Ini cara resmi Next/React menanganinya
  // (lihat next docs "preventing-flash-before-hydration") — bukan menutupi bug
  // kita; atribut itu bukan dari kode kita.
  return (
    <html lang="id" className="h-full antialiased" suppressHydrationWarning>
      <body className="min-h-full" suppressHydrationWarning>
        <StoreProvider>{children}</StoreProvider>
      </body>
    </html>
  );
}
