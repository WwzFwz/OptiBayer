// Halaman 404 — bila URL tak dikenal (app ini SPA satu rute, jadi ini jarang
// muncul; tetap disediakan agar tidak jatuh ke halaman default Next polos).
import Link from "next/link";
import { C } from "@/lib/theme";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-6 text-center"
         style={{ background: C.page, color: C.ink }}>
      <p className="text-5xl font-black" style={{ color: C.accent }}>404</p>
      <p className="text-sm" style={{ color: C.ink2 }}>
        Halaman tidak ditemukan. OptiBayer berjalan di satu rute konsol.
      </p>
      <Link href="/"
        className="rounded-lg px-4 py-2 text-sm font-semibold"
        style={{ background: C.accent, color: "#1a1408" }}>
        Kembali ke Konsol
      </Link>
    </div>
  );
}
