"use client";
// Error boundary global — mencegah "layar putih blank" bila ada komponen
// yang melempar saat runtime (mis. bentuk data API tak terduga). Next.js
// otomatis membungkus konten dengan ini (App Router).
import { useEffect } from "react";
import { C } from "@/lib/theme";

export default function Error({
  error, reset,
}: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    // dicatat ke konsol utk diagnosis; tak menghentikan UI
    console.error("[OptiBayer] runtime error:", error);
  }, [error]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-6 text-center"
         style={{ background: C.page, color: C.ink }}>
      <div className="rounded-xl p-6" style={{ background: C.surface, border: `1px solid ${C.grid}`, maxWidth: 460 }}>
        <p className="mb-1 text-lg font-bold">Terjadi kesalahan tak terduga</p>
        <p className="mb-4 text-sm" style={{ color: C.ink2 }}>
          Komponen gagal dirender. Data mungkin tak sesuai bentuk yang
          diharapkan, atau backend mengirim respons tak lazim. Coba muat ulang
          bagian ini — state lain tetap aman.
        </p>
        {error?.message && (
          <pre className="mb-4 max-h-32 overflow-auto rounded p-2 text-left text-xs"
               style={{ background: C.page, color: C.muted, border: `1px solid ${C.grid}` }}>
            {error.message}
          </pre>
        )}
        <div className="flex justify-center gap-2">
          <button onClick={reset}
            className="btn-lift rounded-lg px-4 py-2 text-sm font-semibold"
            style={{ background: C.accent, color: "#1a1408" }}>
            Coba lagi
          </button>
          <button onClick={() => (window.location.href = "/")}
            className="rounded-lg px-4 py-2 text-sm font-semibold"
            style={{ border: `1px solid ${C.grid}`, color: C.ink2 }}>
            Ke Beranda
          </button>
        </div>
      </div>
    </div>
  );
}
