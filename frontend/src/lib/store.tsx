"use client";
// Store replay OptiBayer — pengganti session_state Streamlit.
// Play berjalan murni di klien (interval) → mulus; data per jam dari REST API
// (fast saat playing, full saat pause — meniru perilaku Streamlit kita).

import React, {
  createContext, useCallback, useContext, useEffect, useRef, useState,
} from "react";
import { getHour, getReplay, HourData, ReplaySeq } from "./api";

export type Dock = "top" | "right";

type Store = {
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
  decide: (key: string, d: "terima" | "tolak") => void;
};

const Ctx = createContext<Store | null>(null);

export function useStore(): Store {
  const s = useContext(Ctx);
  if (!s) throw new Error("useStore di luar <StoreProvider>");
  return s;
}

export function StoreProvider({ children }: { children: React.ReactNode }) {
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

  const decide = useCallback((key: string, d: "terima" | "tolak") => {
    setDecisions((prev) => ({ ...prev, [key]: d }));
  }, []);

  return (
    <Ctx.Provider value={{
      scenario, setScenario, hour, setHour, playing, setPlaying,
      speedMs, setSpeedMs, seq, hourData, loadingHour, apiDown,
      dock, setDock, panelOpen, setPanelOpen, decisions, decide,
    }}>
      {children}
    </Ctx.Provider>
  );
}
