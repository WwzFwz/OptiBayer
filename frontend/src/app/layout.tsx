import type { Metadata } from "next";
import { connection } from "next/server";
import { Suspense } from "react";
import "./globals.css";
import { StoreProvider } from "@/lib/store";
import { ToastProvider } from "@/components/ui/Toast";

// Font sistem (bukan next/font/google) supaya build & runtime tidak butuh
// internet — penting untuk jaringan pabrik tertutup.
export const metadata: Metadata = {
  title: "OptiBayer — CRO Console",
  description:
    "Bayer Process Advisor: digital twin neuro-symbolic untuk pabrik alumina",
};

// Konfigurasi RUNTIME alamat API.
//
// `NEXT_PUBLIC_*` ditanam ke bundle saat BUILD, sehingga image yang sudah jadi
// tidak bisa diarahkan ulang ke backend lain — menyakitkan saat deploy, karena
// URL backend baru diketahui SETELAH backend-nya hidup. Nilai di bawah dibaca
// dari environment server dan disuntikkan ke halaman, jadi satu image yang
// sama bisa dipakai di lokal, staging, dan produksi hanya dengan restart.
// `NEXT_PUBLIC_API_URL` tetap dihormati sebagai cadangan (lihat lib/api.ts).
//
// `await connection()` WAJIB di sini: tanpanya komponen ini ikut masuk shell
// statis dan `process.env` dibaca saat BUILD (terbukti: HTML hasil build tidak
// memuat suntikan sama sekali). Memanggilnya menunda render ke waktu
// permintaan, dan `<Suspense>` di pemakainya menjaga sisa halaman tetap
// statis.
async function SkripKonfigurasi() {
  await connection();
  const api = process.env.OPTIBAYER_API_URL;
  if (!api) return null;
  return (
    <script
      // Hanya menulis satu string ke window sebelum React jalan.
      dangerouslySetInnerHTML={{
        __html: `window.__OPTIBAYER_API__=${JSON.stringify(api)}`,
      }}
    />
  );
}

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
      <head>
        <Suspense fallback={null}><SkripKonfigurasi /></Suspense>
      </head>
      <body className="min-h-full" suppressHydrationWarning>
        <StoreProvider>
          <ToastProvider>{children}</ToastProvider>
        </StoreProvider>
      </body>
    </html>
  );
}
