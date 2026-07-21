"use client";
// Prediction Lab — komposisi & setpoint bebas → ML vs kalkulator fisika.
import { useState } from "react";
import { postOp } from "@/lib/api";
import { C } from "@/lib/theme";

const OXIDES = [
  ["al2o3_pct", "Al₂O₃", 56], ["reactive_sio2_pct", "Silika Reaktif", 4.7],
  ["fe2o3_pct", "Fe₂O₃", 18.5], ["tio2_pct", "TiO₂", 1.6],
  ["cao_pct", "CaO", 0.9], ["mgo_pct", "MgO", 0.6],
  ["na2o_pct", "Na₂O", 0.15], ["k2o_pct", "K₂O", 0.3],
  ["cr2o3_pct", "Cr₂O₃", 0.08],
] as const;
const KNOBS = [
  ["particle_size_um", "Ukuran Partikel (µm)", 62, 50, 75],
  ["digester_temp_c", "Suhu Digester (°C)", 145, 140, 150],
  ["naoh_conc_gl", "Konsentrasi NaOH (g/L)", 150, 140, 160],
  ["precip_temp_c", "Suhu Presipitasi (°C)", 60, 50, 70],
  ["seed_ratio", "Rasio Seed", 2.5, 2, 3],
] as const;
const TARGETS = [
  ["recovery_pct", "Recovery Al", "%"], ["total_opex", "OPEX/jam", ""],
  ["red_mud_t", "Red Mud", "t"], ["precip_yield_pct", "Yield Presip.", "%"],
] as const;

export default function Lab() {
  const [comp, setComp] = useState<Record<string, number>>(
    Object.fromEntries(OXIDES.map(([k, , v]) => [k, v])));
  const [knobs, setKnobs] = useState<Record<string, number>>(
    Object.fromEntries(KNOBS.map(([k, , v]) => [k, v])));
  const [ml, setMl] = useState<Record<string, number> | null>(null);
  const [phys, setPhys] = useState<Record<string, number> | null>(null);
  const [busy, setBusy] = useState(false);

  const sum9 = Object.values(comp).reduce((a, b) => a + b, 0);
  const others = 100 - sum9;

  async function run() {
    setBusy(true);
    const full = { ...comp, others_pct: Math.max(others, 0) };
    try {
      const [p1, p2] = await Promise.all([
        postOp("predict", { composition: full, knobs }),
        postOp("mass-balance", { composition: full, knobs }),
      ]);
      setMl(p1.result); setPhys(p2.result);
    } finally { setBusy(false); }
  }

  return (
    <div className="space-y-3">
      <div className="rounded-xl p-3" style={{ background: C.surface, border: `1px solid ${C.grid}` }}>
        <p className="mb-2 text-sm font-semibold" style={{ color: C.ink }}>Komposisi Bauksit Masuk</p>
        <div className="grid grid-cols-3 gap-3">
          {OXIDES.map(([k, lbl]) => (
            <Slider key={k} label={lbl} val={comp[k]} min={0} max={80} step={0.1}
                    onChange={(v) => setComp({ ...comp, [k]: v })} />
          ))}
        </div>
        <p className="mt-2 text-xs" style={{ color: others < 0 ? C.status.critical : C.muted }}>
          Lain-lain/LOI otomatis: {others.toFixed(2)}% {others < 0 && "(melebihi 100%!)"}
        </p>
      </div>

      <div className="rounded-xl p-3" style={{ background: C.surface, border: `1px solid ${C.grid}` }}>
        <p className="mb-2 text-sm font-semibold" style={{ color: C.ink }}>Parameter Proses</p>
        <div className="grid grid-cols-5 gap-3">
          {KNOBS.map(([k, lbl, , lo, hi]) => (
            <Slider key={k} label={lbl} val={knobs[k]} min={lo} max={hi} step={0.1}
                    onChange={(v) => setKnobs({ ...knobs, [k]: v })} />
          ))}
        </div>
      </div>

      <button onClick={run} disabled={busy}
        className="rounded-lg px-4 py-2 font-semibold"
        style={{ background: C.series[0], color: "#fff", opacity: busy ? 0.6 : 1 }}>
        {busy ? "Menghitung…" : "Prediksi (ML vs Fisika)"}
      </button>

      {ml && phys && (
        <div className="rounded-xl p-3" style={{ background: C.surface, border: `1px solid ${C.grid}` }}>
          <div className="grid grid-cols-2 gap-4">
            <Col title="🤖 Model ML (LightGBM)" data={ml} />
            <Col title="🧮 Kalkulator Fisika (Excel)" data={phys} />
          </div>
        </div>
      )}
    </div>
  );
}
function Slider({ label, val, min, max, step, onChange }: {
  label: string; val: number; min: number; max: number; step: number;
  onChange: (v: number) => void;
}) {
  return (
    <div>
      <label className="text-xs" style={{ color: C.ink2 }}>{label}: {val}</label>
      <input type="range" min={min} max={max} step={step} value={val}
             onChange={(e) => onChange(Number(e.target.value))} className="w-full" />
    </div>
  );
}
function Col({ title, data }: { title: string; data: Record<string, number> }) {
  return (
    <div>
      <p className="mb-2 text-sm font-semibold" style={{ color: C.ink }}>{title}</p>
      {TARGETS.map(([k, lbl, u]) => (
        <div key={k} className="mb-1 flex justify-between text-sm">
          <span style={{ color: C.muted }}>{lbl}</span>
          <span style={{ color: C.ink }}>
            {data[k] !== undefined ? `${data[k].toLocaleString("id-ID", { maximumFractionDigits: 1 })} ${u}` : "—"}
          </span>
        </div>
      ))}
    </div>
  );
}
