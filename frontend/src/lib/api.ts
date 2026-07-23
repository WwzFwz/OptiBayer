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
};
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
