"use client";
// Store replay OptiBayer — pengganti session_state Streamlit.
// Play berjalan murni di klien (interval) → mulus; data per jam dari REST API
// (fast saat playing, full saat pause — meniru perilaku Streamlit kita).

import React, {
  createContext, useCallback, useContext, useEffect, useRef, useState,
} from "react";
import { catatKeputusan, getHour, getReplay, HourData, ReplaySeq } from "./api";
import { isPageId, PageId } from "./pages";

export type Dock = "top" | "right";

/**
 * Keadaan backend dari sudut pandang UI.
 *
 * "menyiapkan" ada karena hosting gratis (HF Spaces / Render free) menidurkan
 * container saat menganggur; permintaan pertama pengunjung membangunkannya dan
 * itu memang makan 30-60 detik. Sebelum ini keadaan tersebut tidak dibedakan
 * dari backend yang benar-benar mati, sehingga pengunjung pertama disambut
 * "API terputus" berwarna merah — dibaca sebagai aplikasi rusak, padahal
 * servernya sedang bangun dan akan hidup sebentar lagi. Kondisi teknisnya
 * sama, kesimpulan pembacanya berbeda jauh.
 */
export type ApiState = "menyiapkan" | "hidup" | "mati";

/** Selama tenggang ini, kegagalan DIANGGAP cold start — bukan backend mati. */
const TENGGANG_MENYIAPKAN_MS = 90_000;
/** Jarak antar-percobaan saat masih menyiapkan (cold start berlangsung). */
const JEDA_MENYIAPKAN_MS = 4_000;
/** Jarak antar-percobaan saat sudah dinyatakan mati — cukup untuk pulih
 *  otomatis kalau backend kembali, tanpa membanjiri jaringan. */
const JEDA_MATI_MS = 15_000;

type Store = {
  page: PageId;                  // halaman aktif (ikut tersimpan di URL)
  setPage: (p: PageId) => void;
  scenario: number;              // 0 normal, 1 spike
  setScenario: (s: number) => void;
  hour: number;
  setHour: (h: number) => void;
  playing: boolean;
  setPlaying: (p: boolean) => void;
  speedMs: number;
  setSpeedMs: (v: number) => void;
  seq: ReplaySeq | null;
  hourData: HourData | null;
  loadingHour: boolean;
  apiState: ApiState;
  /** true setelah replay pernah dijalankan — dipakai utk menyorot ajakan Play */
  pernahMain: boolean;
  dock: Dock;                    // posisi panel advisory (drag utk memindah)
  setDock: (d: Dock) => void;
  panelOpen: boolean;            // Panel Kendali (overlay kiri)
  setPanelOpen: (v: boolean) => void;
  decisions: Record<string, "terima" | "tolak">;
  decide: (key: string, d: "terima" | "tolak", judul: string) => void;
  /** naik tiap kali pencatatan audit GAGAL — dipakai UI utk memberi tahu */
  gagalCatat: number;
};

const Ctx = createContext<Store | null>(null);

export function useStore(): Store {
  const s = useContext(Ctx);
  if (!s) throw new Error("useStore di luar <StoreProvider>");
  return s;
}

export function StoreProvider({ children }: { children: React.ReactNode }) {
  const [page, setPageRaw] = useState<PageId>("overview");
  const [scenario, setScenarioRaw] = useState(1); // default: demo spike
  const [hour, setHour] = useState(8);
  const [playing, setPlayingRaw] = useState(false);
  const [pernahMain, setPernahMain] = useState(false);
  const [speedMs, setSpeedMs] = useState(2000);
  const [seq, setSeq] = useState<ReplaySeq | null>(null);
  const [hourData, setHourData] = useState<HourData | null>(null);
  const [loadingHour, setLoadingHour] = useState(false);
  const [apiState, setApiState] = useState<ApiState>("menyiapkan");
  // Token percobaan ulang: dinaikkan timer, ikut jadi dependensi efek fetch
  // supaya permintaan diulang tanpa pengunjung harus me-refresh halaman.
  const [percobaan, setPercobaan] = useState(0);
  const [kegagalan, setKegagalan] = useState(0);
  const pernahHidup = useRef(false);
  const gagalPertama = useRef<number | null>(null);
  // preferensi dock dibaca sekali via lazy initializer (bukan efek) — hindari
  // setState-in-effect & flicker. Guard SSR: localStorage tak ada di server.
  const [dock, setDockRaw] = useState<Dock>(() => {
    if (typeof window === "undefined") return "right";
    const saved = window.localStorage.getItem("optibayer.dock");
    return saved === "right" || saved === "top" ? saved : "right";
  });
  const [panelOpen, setPanelOpen] = useState(false);
  const [decisions, setDecisions] = useState<Record<string, "terima" | "tolak">>({});
  const [gagalCatat, setGagalCatat] = useState(0);
  const reqId = useRef(0);

  const setDock = useCallback((d: Dock) => {
    setDockRaw(d);
    localStorage.setItem("optibayer.dock", d);
  }, []);

  const setScenario = useCallback((s: number) => {
    setScenarioRaw(s);
    setHour(8);
    setPlayingRaw(false);
  }, []);

  // `pernahMain` sengaja hidup di store, bukan di komponen tombol: replay bisa
  // dinyalakan dari header MAUPUN Panel Kendali, dan sorotan ajakan harus padam
  // begitu salah satunya dipakai.
  const setPlaying = useCallback((p: boolean) => {
    setPlayingRaw(p);
    if (p) setPernahMain(true);
  }, []);

  // ------------------------------------------------------- keadaan backend
  const tandaiHidup = useCallback(() => {
    pernahHidup.current = true;
    setApiState("hidup");
  }, []);

  const tandaiGagal = useCallback(() => {
    // Kegagalan hanya boleh disebut "mati" kalau backend PERNAH menjawab
    // (berarti benar-benar putus di tengah jalan), atau kalau tenggang cold
    // start sudah lewat. Sebelum itu, ini masih wajar.
    //
    // Tenggang dihitung sejak kegagalan PERTAMA, bukan sejak halaman dibuka:
    // `Date.now()` tak boleh dipanggil saat render (aturan kemurnian React),
    // dan patokan ini justru lebih tepat — yang sedang diberi waktu adalah
    // proses membangunkan container, dan itu baru diketahui saat permintaan
    // pertama gagal.
    const kini = Date.now();
    if (gagalPertama.current === null) gagalPertama.current = kini;
    const masihTenggang = kini - gagalPertama.current < TENGGANG_MENYIAPKAN_MS;
    setApiState(!pernahHidup.current && masihTenggang ? "menyiapkan" : "mati");
    setKegagalan((n) => n + 1);
  }, []);

  // Coba lagi otomatis. Tanpa ini pengunjung yang mendarat saat container masih
  // bangun akan terjebak di layar kosong sampai dia berinisiatif me-refresh —
  // dan pengunjung yang mengira aplikasinya rusak tidak akan me-refresh.
  useEffect(() => {
    if (kegagalan === 0 || apiState === "hidup") return;
    const jeda = apiState === "menyiapkan" ? JEDA_MENYIAPKAN_MS : JEDA_MATI_MS;
    const t = setTimeout(() => setPercobaan((n) => n + 1), jeda);
    return () => clearTimeout(t);
  }, [kegagalan, apiState]);

  // ------------------------------------------------------------------ URL
  // Halaman/skenario/jam disimpan di query string supaya keadaan layar bisa
  // DI-LINK ("lihat Red Mud jam 14"), tombol Back browser berfungsi, dan
  // refresh tidak melempar balik ke Overview. Sebelumnya seluruh aplikasi
  // hidup di satu rute tanpa jejak URL sama sekali.
  //
  // Pembacaan awal sengaja dilakukan di efek (bukan lazy initializer) supaya
  // markup hasil prerender identik dengan render pertama di klien — tidak ada
  // ketidakcocokan hidrasi.
  const urlSiap = useRef(false);

  // HATI-HATI: `URLSearchParams.get` mengembalikan null kalau parameter tidak
  // ada, dan `Number(null) === 0`. Kalau nilai mentahnya tidak diperiksa lebih
  // dulu, membuka aplikasi di "/" polos akan diam-diam memaksa skenario ke 0
  // (Operasi Normal) dan jam ke 0 — bukan default demo (spike, jam 8).
  const terapkanUrl = useCallback((q: URLSearchParams) => {
    const p = q.get("p");
    if (isPageId(p)) setPageRaw(p);

    const sMentah = q.get("s");
    if (sMentah !== null) {
      const s = Number(sMentah);
      if (s === 0 || s === 1) setScenarioRaw(s);
    }

    const hMentah = q.get("h");
    if (hMentah !== null) {
      const h = Number(hMentah);
      if (Number.isFinite(h) && h >= 0) setHour(Math.floor(h));
    }
  }, []);

  useEffect(() => {
    // sinkronisasi dgn sistem eksternal (URL) — bukan turunan state lain
    // eslint-disable-next-line react-hooks/set-state-in-effect
    terapkanUrl(new URLSearchParams(window.location.search));
    urlSiap.current = true;

    const kembali = () =>
      terapkanUrl(new URLSearchParams(window.location.search));
    window.addEventListener("popstate", kembali);
    return () => window.removeEventListener("popstate", kembali);
  }, [terapkanUrl]);

  // Tulis balik ke URL. `replaceState` dipakai untuk jam/skenario supaya
  // menggeser slider tidak membanjiri riwayat browser; perpindahan HALAMAN
  // memakai pushState (lewat setPage) agar Back terasa wajar.
  useEffect(() => {
    if (!urlSiap.current) return;
    const q = new URLSearchParams(window.location.search);
    q.set("p", page);
    q.set("s", String(scenario));
    q.set("h", String(hour));
    window.history.replaceState(null, "", `?${q.toString()}`);
  }, [page, scenario, hour]);

  const setPage = useCallback((p: PageId) => {
    setPageRaw(p);
    if (typeof window === "undefined") return;
    const q = new URLSearchParams(window.location.search);
    q.set("p", p);
    window.history.pushState(null, "", `?${q.toString()}`);
  }, []);

  // deret tren per skenario
  useEffect(() => {
    let alive = true;
    getReplay(scenario)
      .then((d) => alive && (setSeq(d), tandaiHidup()))
      .catch(() => alive && tandaiGagal());
    return () => { alive = false; };
  }, [scenario, percobaan, tandaiHidup, tandaiGagal]);

  // data jam aktif: fast saat playing, full saat pause
  useEffect(() => {
    const id = ++reqId.current;
    // sinkronisasi state loading dgn efek fetch eksternal — memang disengaja
    // (pola "synchronize with external system", bukan turunan state lain).
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoadingHour(true);
    getHour(scenario, hour, playing)
      .then((d) => {
        if (reqId.current !== id) return; // respons basi diabaikan
        setHourData(d);
        tandaiHidup();
      })
      .catch(() => reqId.current === id && tandaiGagal())
      .finally(() => reqId.current === id && setLoadingHour(false));
  }, [scenario, hour, playing, percobaan, tandaiHidup, tandaiGagal]);

  // mesin Play — interval klien (bebas rerun ala Streamlit)
  useEffect(() => {
    if (!playing || !seq) return;
    const t = setInterval(() => {
      setHour((h) => {
        if (h >= seq.n - 1) { setPlayingRaw(false); return h; }
        return h + 1;
      });
    }, speedMs);
    return () => clearInterval(t);
  }, [playing, speedMs, seq]);

  // Keputusan operator DICATAT DI SERVER, bukan cuma di memori browser.
  // Sebelumnya nilai ini hilang setiap refresh sementara halaman Audit Trail
  // hanya menampilkan keputusan dari Streamlit — audit trail yang bolong.
  // Status lokal tetap di-set lebih dulu (optimistic) supaya tombol terasa
  // responsif; kalau server menolak, status dikembalikan dan operator diberi
  // tahu, karena mengaku "tercatat" padahal tidak jauh lebih berbahaya
  // daripada gagal terang-terangan.
  const decide = useCallback((key: string, d: "terima" | "tolak",
                              judul: string) => {
    setDecisions((prev) => ({ ...prev, [key]: d }));
    catatKeputusan(hour, judul, d).catch(() => {
      setDecisions((prev) => {
        const salinan = { ...prev };
        delete salinan[key];
        return salinan;
      });
      setGagalCatat((n) => n + 1);
    });
  }, [hour]);

  return (
    <Ctx.Provider value={{
      page, setPage,
      scenario, setScenario, hour, setHour, playing, setPlaying,
      pernahMain,
      speedMs, setSpeedMs, seq, hourData, loadingHour, apiState,
      dock, setDock, panelOpen, setPanelOpen, decisions, decide, gagalCatat,
    }}>
      {children}
    </Ctx.Provider>
  );
}
