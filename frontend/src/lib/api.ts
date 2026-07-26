// Klien REST OptiBayer — satu-satunya pintu frontend ke inti Python.
//
// Urutan penentuan alamat backend, dari yang paling bisa diubah belakangan:
//   1. window.__OPTIBAYER_API__ — disuntik server dari env OPTIBAYER_API_URL
//      pada tiap permintaan (lihat app/layout.tsx). Ini yang membuat SATU image
//      Docker bisa dipakai di lokal, staging, dan produksi tanpa build ulang.
//   2. NEXT_PUBLIC_API_URL — ditanam saat build; tetap didukung utk dev lokal.
//   3. localhost:8000 — default pengembangan.
declare global {
  interface Window { __OPTIBAYER_API__?: string }
}

function alamatApi(): string {
  if (typeof window !== "undefined" && window.__OPTIBAYER_API__) {
    return window.__OPTIBAYER_API__;
  }
  return process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
}

export const API = alamatApi();

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

/** Interval konformal: ±half dgn cakupan `level` (doc 14 C1). */
export type Interval = {
  lo: number; hi: number; half: number; level: number; coverage: number;
};

/** Guard out-of-distribution: apakah titik operasi masih dikuasai model. */
export type Ood = {
  ok: boolean;
  n_out: number;
  labels: string[];
  komposisi_total_pct: number;
  komposisi_wajar: boolean;
  alasan: string[];
};

/** Hasil wasit fisika: prediksi ML vs neraca massa deterministik. */
export type PhysicsCheck = {
  ok: boolean;
  n_gagal?: number;
  gagal_label: string[];
  rows: Array<{
    target: string; label: string; ml: number; fisika: number;
    selisih: number; tol: number; rasio?: number; ok: boolean;
  }>;
  error?: string;
};

export type HourData = {
  hour: number;
  fast: boolean;
  kpi: KPI;
  interval?: Record<string, Interval | null>;
  ood?: Ood;
  physics_check?: PhysicsCheck;
  silika_level: "normal" | "warning" | "critical";
  cards: Card[];
  recommended_knobs: Record<string, number>;
  delta_if_followed: Record<string, number>;
  /** "neraca massa eksak" | "selisih prediksi ML" — dasar angka janji delta */
  delta_basis?: string;
  delta_if_followed_ml?: Record<string, number>;
  na_balance: Record<string, number>;
  carbonation: Record<string, number>;
  al_balance?: Record<string, number>;
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

export type OperatingMap = {
  temps: number[]; naohs: number[]; z: number[][];
  now: { t: number; naoh: number };
  reco: { t: number; naoh: number };
  composition: Record<string, number>;
  knobs_now: Record<string, number>;
  bounds: Record<string, [number, number]>;
  knob_labels: Record<string, string>;
};

export type Sensitivity = {
  target: string;
  curves: Record<string, Array<{ x: number; y: number }>>;
  deltas: Record<string, number>;
  current: Record<string, number>;
  labels: Record<string, string>;
  out_of_bounds: string[];
  ood?: Ood;
  physics_check?: PhysicsCheck;
  interval?: Record<string, Interval | null>;
};

/** Setpoint termurah yang masih mencapai target recovery (endpoint kontrak). */
export type GoalSeek = {
  knobs?: Record<string, number>;
  prediction?: Record<string, number>;
  feasible?: boolean;
  note?: string;
};

export const goalSeek = (
  composition: Record<string, number>, target_recovery: number,
) => postOp("optimize/goal-seek", { composition, target_recovery })
  .then((r) => (r.result ?? r) as GoalSeek);

/** Kartu identitas model: metrik CV + lebar interval konformal per target. */
export type ModelHealth = {
  targets: Record<string, {
    label: string; cv_r2: number; cv_mae: number; n_rows: number;
    half_90: number | null;
    conformal: Record<string, { q: number; coverage_empiris: number }>;
    /** keluarga model dipilih per target lewat adu CV — bukan selalu LightGBM */
    family?: string;
    family_label?: string;
    seleksi?: Record<string, { cv_r2: number; cv_mae: number }>;
  }>;
  catatan: string;
};
export const getModelHealth = () => get<ModelHealth>("/v1/model/health");
export const getSensitivity = (
  composition: Record<string, number>, knobs: Record<string, number>,
) => postOp("sensitivity", { composition, knobs }) as Promise<Sensitivity>;
export const getOperatingMap = (s: number, hour: number) =>
  get<OperatingMap>(`/v1/operating-map?scenario_id=${s}&hour=${hour}`);

export type ParetoData = {
  solutions: Array<Record<string, number>>;
  picked: Record<string, number>;
  bounds: Record<string, [number, number]>;
  now_knobs: Record<string, number>;
  labels: Record<string, string>;
};
export const getPareto = (s: number, hour: number) =>
  get<ParetoData>(`/v1/pareto?scenario_id=${s}&hour=${hour}`);

export type CeqData = {
  temps: number[]; ceq: number[]; a_gl: number;
  t_now: number; ceq_now: number; gap: number;
};
export const getCeq = (a: number, caustic: number, t: number) =>
  get<CeqData>(`/v1/ceq?a_gl=${a}&caustic_gl=${caustic}&t_now=${t}`);

export type KnowledgeDoc = {
  name: string; tags: string[]; status: string; body: string; used_by: string[];
};
export const getKnowledge = () =>
  get<{ docs: KnowledgeDoc[]; charts: Record<string, string> }>("/v1/knowledge");

export async function addKnowledge(payload: {
  name: string; body: string; charts: string[]; extra_tags: string[];
}): Promise<{ ok: boolean; saved: string; tags: string[] }> {
  const r = await fetch(`${API}/v1/knowledge/add`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error((await r.json()).detail ?? `knowledge: ${r.status}`);
  return r.json();
}

export const getContract = () =>
  get<Record<string, unknown>>("/v1/integration/contract");

/** Audit trail keputusan advisory (persisten di server, bukan di memori). */
export type AuditRow = {
  waktu: string; jam_sim: string; judul: string;
  keputusan: string; sumber?: string;
};
export const getAudit = (limit = 20) =>
  get<{ n_total: number; decisions: AuditRow[] }>(`/v1/audit/decisions?limit=${limit}`);

export async function catatKeputusan(
  hour: number, title: string, decision: "terima" | "tolak",
): Promise<void> {
  const r = await fetch(`${API}/v1/audit/decision`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ hour, title, decision, sumber: "react" }),
  });
  if (!r.ok) throw new Error(`audit: ${r.status}`);
}

export type RegretData = {
  actual: Record<string, number>;
  counterfactual: Record<string, number>;
  delta: Record<string, number>;
  series: Array<{ sim_hour: number; actual: number; counterfactual: number }>;
  handover: string;
  handover_backend: string;
};
export const getRegret = (s: number, hour: number) =>
  get<RegretData>(`/v1/regret?scenario_id=${s}&hour=${hour}`);

export type CorrelationData = {
  target: string; target_label: string; feature: string; feature_label: string;
  corr: Array<{ feature: string; label: string; r: number }>;
  scatter: Array<{ x: number; y: number }>;
  features: Array<{ key: string; label: string }>;
  targets: Array<{ key: string; label: string }>;
};
export const getCorrelation = (target: string, feature: string) =>
  get<CorrelationData>(`/v1/correlation?target=${target}&feature=${feature}`);

export async function explainChart(
  title: string, context: unknown, question = "", tags?: string[],
): Promise<{ text: string; backend: string }> {
  const r = await fetch(`${API}/v1/explain`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, context, question, tags }),
  });
  if (!r.ok) throw new Error(`explain: ${r.status}`);
  return r.json();
}

export async function postOp(op: string, payload: unknown) {
  const r = await fetch(`${API}/v1/${op}`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error(`API ${op}: ${r.status}`);
  return r.json();
}
