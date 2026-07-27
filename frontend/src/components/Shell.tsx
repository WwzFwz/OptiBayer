"use client";
// Shell OptiBayer: rail ikon kiri + header + Panel Kendali overlay +
// panel Advisory yang bisa di-dock (atas / kanan, via drag atau toggle).
import { useEffect, useRef } from "react";
import { CircleAlert, Loader2, Pause, Play, Wifi, WifiOff } from "lucide-react";
import { API } from "@/lib/api";
import { useToast } from "./ui/Toast";
import Advisory from "./Advisory";
import ControlPanel from "./ControlPanel";
import Kpi from "./Kpi";
import Rail from "./Rail";
import { PageId } from "@/lib/pages";
import Overview from "./pages/Overview";
import Diagram from "./pages/Diagram";
import Digesti from "./pages/Digesti";
import Liquor from "./pages/Liquor";
import Presipitasi from "./pages/Presipitasi";
import RedMud from "./pages/RedMud";
import Lab from "./pages/Lab";
import Knowledge from "./pages/Knowledge";
import Integrasi from "./pages/Integrasi";
import { useStore } from "@/lib/store";
import { C } from "@/lib/theme";

const REPLAY_FREE: PageId[] = ["lab", "knowledge", "integrasi"];

// Petunjuk "jalankan uvicorn" hanya masuk akal kalau backend memang di mesin
// yang sama. Pengunjung sebuah link publik tidak punya terminal kita, dan
// menyuruhnya menjalankan perintah Python justru menegaskan kesan aplikasinya
// rusak. Di luar lokal, tawarkan tindakan yang benar-benar bisa dia lakukan.
const LOKAL = /localhost|127\.0\.0\.1/.test(API);

export default function Shell() {
  const s = useStore();
  // halaman aktif hidup di store supaya ikut tersinkron ke URL (deep link)
  const { page, setPage } = s;
  const monitoring = !REPLAY_FREE.includes(page);
  const toast = useToast();

  // Kalau server menolak mencatat keputusan, operator HARUS tahu — tombolnya
  // sudah terlanjur memberi kesan "tercatat di audit".
  const gagalTerakhir = useRef(0);
  useEffect(() => {
    if (s.gagalCatat > gagalTerakhir.current) {
      gagalTerakhir.current = s.gagalCatat;
      toast("error", "Keputusan GAGAL dicatat ke audit trail — cek backend, "
                   + "lalu ulangi. Keputusan tadi dibatalkan.");
    }
  }, [s.gagalCatat, toast]);

  const day = Math.floor(s.hour / 24) + 1;
  const clock = s.hour % 24;
  const shift = Math.floor(clock / 8) + 1;
  const scenarioName = s.scenario === 1 ? "Gangguan: Silika Spike" : "Operasi Normal";

  // "menyiapkan" punya dua wajah. Sebelum ada kegagalan nyata kita cuma BELUM
  // tahu — nadanya netral, bukan kuning peringatan, supaya pemuatan yang sehat
  // tidak berkedip seolah bermasalah. Kuning baru dipakai setelah permintaan
  // benar-benar gagal, saat cold start jadi dugaan yang masuk akal.
  const { warna, label } = {
    hidup: { warna: C.status.good, label: "API tersambung" },
    menyiapkan: s.pernahGagal
      ? { warna: C.status.warning, label: "Menyiapkan server…" }
      : { warna: C.muted, label: "Menyambungkan…" },
    mati: { warna: C.status.critical, label: "API terputus" },
  }[s.apiState];

  // Sorotan hanya sampai replay pernah dijalankan sekali — setelah pengunjung
  // tahu tombolnya ada, denyut terus-menerus cuma jadi gangguan. Juga tidak
  // menyorot saat backend belum siap: mengajak menekan tombol yang belum bisa
  // bekerja hanya memindahkan kekecewaan.
  const sorotPlay = !s.pernahMain && !s.playing && s.apiState === "hidup";

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: C.page }}>
      <Rail page={page} setPage={setPage} />
      <ControlPanel />

      <div className="flex min-w-0 flex-1 flex-col">
        {/* header */}
        <header className="flex items-center gap-3 px-4 py-3"
                style={{ borderBottom: `1px solid ${C.grid}` }}>
          <h1 className="text-lg font-bold" style={{ color: C.ink }}>
            OptiBayer <span className="font-normal" style={{ color: C.muted }}>· Konsol CRO</span>
          </h1>
          <span className="text-xs" style={{ color: C.muted }}>
            {monitoring
              ? `Hari ${day} · ${String(clock).padStart(2, "0")}:00 · Shift ${shift} · ${scenarioName}`
              : "Halaman bebas replay"}
          </span>

          {/* Ajakan UTAMA. Sebelumnya Play hanya ada di dalam Panel Kendali —
              overlay yang tertutup secara default di balik satu ikon tanpa
              label di rail. Akibatnya pengunjung baru mendarat di dashboard
              yang diam, tanpa satu pun petunjuk bahwa ada replay untuk
              dijalankan, dan mudah menyimpulkan ini tangkapan layar statis.
              Panel Kendali tetap memegang kendali lanjutan (kecepatan,
              skenario, slider jam); yang naik ke sini hanya aksi utamanya. */}
          {monitoring && (
            <button
              onClick={() => s.setPlaying(!s.playing)}
              aria-pressed={s.playing}
              aria-label={s.playing ? "Jeda simulasi" : "Mulai simulasi"}
              className={`btn-lift ml-2 flex items-center gap-1.5 rounded-lg px-3 py-1.5
                          text-sm font-semibold${sorotPlay ? " pulse-cta" : ""}`}
              style={{
                background: s.playing ? C.status.warning : C.status.good,
                color: "#fff",
              }}
            >
              {s.playing ? <Pause size={15} /> : <Play size={15} />}
              {s.playing ? "Jeda" : "Mulai Simulasi"}
            </button>
          )}

          <span className="ml-auto flex items-center gap-1 text-xs"
                style={{ color: warna }}>
            {s.apiState === "hidup" && <Wifi size={14} />}
            {s.apiState === "menyiapkan" && <Loader2 size={14} className="spin-ikon" />}
            {s.apiState === "mati" && <WifiOff size={14} />}
            {label}
          </span>
        </header>

        {s.apiState === "menyiapkan" && s.pernahGagal && (
          <div className="flex items-center gap-2 px-4 py-2 text-sm"
               style={{ background: "#fab21922", color: C.status.warning }}>
            <Loader2 size={16} className="spin-ikon" />
            Menyiapkan server — kunjungan pertama biasanya butuh 30–60 detik.
            Halaman ini akan mengisi sendiri, tidak perlu dimuat ulang.
          </div>
        )}

        {s.apiState === "mati" && (
          <div className="flex items-center gap-2 px-4 py-2 text-sm"
               style={{ background: "#d03b3b22", color: C.status.critical }}>
            <CircleAlert size={16} />
            {LOKAL ? (
              <>
                Backend belum jalan — jalankan:&nbsp;
                <code style={{ color: C.ink2 }}>
                  python -m uvicorn src.integration.api:app --port 8000
                </code>
              </>
            ) : (
              <>Server tidak merespons. Percobaan ulang berjalan otomatis tiap
                 15 detik — biarkan tab ini terbuka sebentar.</>
            )}
          </div>
        )}

        {/* konten + dock kanan */}
        <div className="flex min-h-0 flex-1">
          <main className="min-w-0 flex-1 space-y-3 overflow-y-auto p-4">
            {monitoring && <Kpi />}
            {/* advisory bisa di-drag: dock atas (di sini) atau kanan (aside) */}
            {monitoring && s.dock === "top" && <Advisory setPage={setPage} />}
            {/* key=page → fade-in ulang tiap ganti halaman (transisi halus) */}
            <div key={page} className="fade-in space-y-3">
              {page === "overview" && <Overview />}
              {page === "diagram" && <Diagram />}
              {page === "digesti" && <Digesti />}
              {page === "liquor" && <Liquor />}
              {page === "presipitasi" && <Presipitasi />}
              {page === "redmud" && <RedMud />}
              {page === "lab" && <Lab />}
              {page === "knowledge" && <Knowledge />}
              {page === "integrasi" && <Integrasi />}
            </div>
          </main>
          {monitoring && s.dock === "right" && (
            <aside className="w-[340px] shrink-0 overflow-y-auto p-3"
                   style={{ borderLeft: `1px solid ${C.grid}` }}>
              <Advisory setPage={setPage} />
            </aside>
          )}
        </div>
      </div>
    </div>
  );
}

