// Klien REST OptiBayer — satu-satunya pintu frontend ke inti Python.
// Base URL dari env (NEXT_PUBLIC_API_URL); default localhost:8000.
export const API =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Card = {
  severity: "critical" | "serious" | "warning" | "info";
  title: string;
  impact: string;
  action: string;
  why: string;
  confidence: string;
};

export type KPI = {
  recovery_pct: number;
  total_opex: number;
  reactive_sio2_pct: number;
  red_mud_t: number;
  co2_capture_t: number;
  precip_yield_pct: number;
};

export type HourData = {
  hour: number;
  fast: boolean;
  kpi: KPI;
  silika_level: "normal" | "warning" | "critical";
  cards: Card[];
  recommended_knobs: Record<string, number>;
  delta_if_followed: Record<string, number>;
  na_balance: Record<string, number>;
  carbonation: Record<string, number>;
};

export type ReplaySeq = {
  scenario: string;
  n: number;
  hours: Array<Record<string, number>>;
};

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${API}${path}`, { cache: "no-store" });
  if (!r.ok) throw new Error(`API ${path}: ${r.status}`);
  return r.json();
}

export const getReplay = (s: number) =>
  get<ReplaySeq>(`/v1/replay/${s}`);

export const getHour = (s: number, hour: number, fast = true) =>
  get<HourData>(`/v1/replay/${s}/hour/${hour}?fast=${fast}`);

export const getHealth = () => get<{ ok: boolean }>("/v1/health");
