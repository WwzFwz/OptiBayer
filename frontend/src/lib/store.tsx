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
  apiDown: boolean;
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
  const [playing, setPlaying] = useState(false);
  const [speedMs, setSpeedMs] = useState(2000);
  const [seq, setSeq] = useState<ReplaySeq | null>(null);
  const [hourData, setHourData] = useState<HourData | null>(null);
  const [loadingHour, setLoadingHour] = useState(false);
  const [apiDown, setApiDown] = useState(false);
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
    setPlaying(false);
  }, []);

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
      .then((d) => alive && (setSeq(d), setApiDown(false)))
      .catch(() => alive && setApiDown(true));
    return () => { alive = false; };
  }, [scenario]);

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
        setApiDown(false);
      })
      .catch(() => reqId.current === id && setApiDown(true))
      .finally(() => reqId.current === id && setLoadingHour(false));
  }, [scenario, hour, playing]);

  // mesin Play — interval klien (bebas rerun ala Streamlit)
  useEffect(() => {
    if (!playing || !seq) return;
    const t = setInterval(() => {
      setHour((h) => {
        if (h >= seq.n - 1) { setPlaying(false); return h; }
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
      speedMs, setSpeedMs, seq, hourData, loadingHour, apiDown,
      dock, setDock, panelOpen, setPanelOpen, decisions, decide, gagalCatat,
    }}>
      {children}
    </Ctx.Provider>
  );
}
