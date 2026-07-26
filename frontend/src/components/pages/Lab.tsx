"use client";
// Prediction Lab — komposisi & setpoint bebas → ML vs kalkulator fisika.
import { useState } from "react";
import {
  Bar, BarChart, Cell, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import {
  getModelHealth, getSensitivity, goalSeek, GoalSeek, ModelHealth,
  postOp, Sensitivity,
} from "@/lib/api";
import { Spinner } from "@/components/ui/Feedback";
import { useToast } from "@/components/ui/Toast";
import { TrustBar } from "@/components/ui/Trust";
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
  const [sens, setSens] = useState<Sensitivity | null>(null);
  const [busy, setBusy] = useState(false);
  const [health, setHealth] = useState<ModelHealth | null>(null);
  const [targetRec, setTargetRec] = useState(88);
  const [gs, setGs] = useState<GoalSeek | null>(null);
  const [gsBusy, setGsBusy] = useState(false);
  const toast = useToast();

  const sum9 = Object.values(comp).reduce((a, b) => a + b, 0);
  const others = 100 - sum9;
  const komposisiPenuh = () => ({ ...comp, others_pct: Math.max(others, 0) });

  async function run() {
    setBusy(true);
    const full = komposisiPenuh();
    try {
      const [p1, p2, s, h] = await Promise.all([
        postOp("predict", { composition: full, knobs }),
        postOp("mass-balance", { composition: full, knobs }),
        getSensitivity(full, knobs),
        getModelHealth().catch(() => null),
      ]);
      setMl(p1.result); setPhys(p2.result); setSens(s);
      if (h) setHealth(h);
    } catch (e) {
      toast("error", `Gagal menghitung — cek backend (port 8000). ${e}`);
    } finally { setBusy(false); }
  }

  // Goal-seek: "berapa setpoint TERMURAH yang masih mencapai recovery X?".
  // Endpoint-nya sudah ada di kontrak sejak awal tapi belum pernah punya UI —
  // sebelumnya hanya bisa dipanggil lewat Python (doc 14 C5).
  async function cariSetpoint() {
    setGsBusy(true);
    try {
      const r = await goalSeek(komposisiPenuh(), targetRec);
      setGs(r);
      if (r.feasible === false) {
        toast("info", `Recovery ${targetRec}% tidak tercapai untuk komposisi ini.`);
      } else if (r.knobs) {
        setKnobs({ ...knobs, ...r.knobs });
        toast("success", "Setpoint termurah ditemukan & dimuat ke slider.");
      }
    } catch (e) {
      toast("error", `Goal-seek gagal — cek backend. ${e}`);
    } finally { setGsBusy(false); }
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

      <div className="flex flex-wrap items-end gap-3">
        <button onClick={run} disabled={busy}
          className="btn-lift inline-flex items-center gap-2 rounded-lg px-4 py-2 font-semibold"
          style={{ background: C.accent, color: "#1a1408", opacity: busy ? 0.6 : 1 }}>
          {busy && <Spinner />}{busy ? "Menghitung…" : "Prediksi (ML vs Fisika)"}
        </button>

        {/* Goal-seek — arah terbalik: tentukan hasil, biar mesin cari setpoint */}
        <div className="flex items-end gap-2 rounded-lg px-3 py-2"
             style={{ background: C.surface, border: `1px solid ${C.grid}` }}>
          <label className="text-xs" style={{ color: C.ink2 }}>
            <span className="mb-1 block">Target recovery (%)</span>
            <input type="number" value={targetRec} min={70} max={99} step={0.5}
                   onChange={(e) => setTargetRec(Number(e.target.value))}
                   className="w-20 rounded px-2 py-1 tabular-nums"
                   style={{ background: C.page, color: C.ink, border: `1px solid ${C.grid}` }} />
          </label>
          <button onClick={cariSetpoint} disabled={gsBusy}
            className="btn-lift inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-semibold"
            style={{ background: C.page, color: C.ink,
                     border: `1px solid ${C.grid}`, opacity: gsBusy ? 0.6 : 1 }}>
            {gsBusy && <Spinner />}Cari setpoint termurah
          </button>
        </div>
      </div>

      {gs && (
        <div className="rounded-xl p-3 text-sm"
             style={{ background: C.surface, border: `1px solid ${C.grid}` }}>
          <p className="mb-1 font-semibold" style={{ color: C.ink }}>
            Goal-seek: recovery ≥ {targetRec}%
          </p>
          {gs.feasible === false || !gs.prediction ? (
            <p style={{ color: C.status.warning }}>
              {gs.note ?? "Target tidak tercapai dalam amplop operasi aman."}
            </p>
          ) : (
            <p style={{ color: C.ink2 }}>
              Recovery {gs.prediction.recovery_pct?.toFixed(2)}% dengan OPEX{" "}
              {gs.prediction.total_opex?.toLocaleString("id-ID", { maximumFractionDigits: 0 })}/jam.
              Setpoint hasil pencarian sudah dimuat ke slider di atas — tekan
              “Prediksi (ML vs Fisika)” untuk memverifikasinya dengan neraca massa.
            </p>
          )}
        </div>
      )}

      {sens && <TrustBar ood={sens.ood} physics={sens.physics_check} />}

      {sens && sens.out_of_bounds.length > 0 && (
        <div className="rounded-lg p-3 text-sm"
             style={{ background: "#fab21922", color: C.status.warning, border: `1px solid ${C.status.warning}` }}>
          ⚠️ <b>Ekstrapolasi</b> — di luar rentang data latih untuk:{" "}
          {sens.out_of_bounds.join(", ")}. Prediksi ML kurang bisa dipercaya di
          titik ini; kalkulator fisika tetap berlaku penuh (deterministik).
        </div>
      )}

      {ml && phys && (
        <div className="rounded-xl p-3" style={{ background: C.surface, border: `1px solid ${C.grid}` }}>
          <div className="grid grid-cols-2 gap-4">
            <Col title="🤖 Surrogate ML" data={ml} health={health} />
            <Col title="🧮 Kalkulator Fisika (Excel)" data={phys} />
          </div>
          {health && (
            <p className="mt-2 text-[0.68rem]" style={{ color: C.muted }}>
              Keluarga model dipilih per target lewat adu validasi silang, jadi
              tidak semuanya LightGBM — lihat label kecil di tiap baris.
            </p>
          )}
        </div>
      )}

      {sens && (
        <div className="rounded-xl p-3" style={{ background: C.surface, border: `1px solid ${C.grid}` }}>
          <p className="mb-2 text-sm font-semibold" style={{ color: C.ink }}>
            Simulasi What-If Parameter — sensitivitas pada komposisi ini
          </p>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
            {Object.keys(sens.labels).map((k) => (
              <div key={k}>
                <p className="mb-1 text-xs" style={{ color: C.ink2 }}>{sens.labels[k].split(" ")[0]}</p>
                <ResponsiveContainer width="100%" height={90}>
                  <LineChart data={sens.curves[k]}>
                    <Line type="monotone" dataKey="y" stroke={C.series[0]} strokeWidth={2}
                          dot={false} isAnimationActive={false} />
                    <XAxis dataKey="x" hide /><YAxis hide domain={["auto", "auto"]} />
                    <Tooltip contentStyle={{ background: C.page, border: `1px solid ${C.grid}`, borderRadius: 6 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            ))}
          </div>
          <p className="mb-1 mt-3 text-xs font-semibold" style={{ color: C.ink2 }}>
            Ranking pengaruh (Δ ujung-ke-ujung rentang aman)
          </p>
          {(() => {
            const tornado = Object.keys(sens.deltas)
              .map((k) => ({ name: sens.labels[k].split(" ")[0], d: sens.deltas[k] }))
              .sort((a, b) => Math.abs(b.d) - Math.abs(a.d));
            return (
              <ResponsiveContainer width="100%" height={160}>
                <BarChart layout="vertical" data={tornado}>
                  <XAxis type="number" stroke={C.muted} fontSize={11} />
                  <YAxis type="category" dataKey="name" stroke={C.muted} fontSize={11} width={90} />
                  <Tooltip contentStyle={{ background: C.page, border: `1px solid ${C.grid}`, borderRadius: 8 }} />
                  <Bar dataKey="d">
                    {tornado.map((t, i) => (
                      <Cell key={i} fill={t.d >= 0 ? C.status.good : C.status.critical} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            );
          })()}
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
function Col({ title, data, health }: {
  title: string; data: Record<string, number>; health?: ModelHealth | null;
}) {
  return (
    <div>
      <p className="mb-2 text-sm font-semibold" style={{ color: C.ink }}>{title}</p>
      {TARGETS.map(([k, lbl, u]) => {
        const info = health?.targets?.[k];
        return (
          <div key={k} className="mb-1 flex items-baseline justify-between gap-2 text-sm">
            <span style={{ color: C.muted }}>
              {lbl}
              {info?.family && (
                <span className="ml-1 text-[0.6rem] uppercase tracking-wide"
                      title={info.family_label ?? info.family}
                      style={{ color: C.muted, opacity: 0.75 }}>
                  {info.family}
                </span>
              )}
            </span>
            <span className="text-right" style={{ color: C.ink }}>
              {data[k] !== undefined
                ? `${data[k].toLocaleString("id-ID", { maximumFractionDigits: 1 })} ${u}`
                : "—"}
              {info?.half_90 != null && (
                <span className="ml-1 text-[0.68rem]" style={{ color: C.muted }}
                      title={`Interval konformal 90% dari residual validasi silang`}>
                  ±{info.half_90.toLocaleString("id-ID", { maximumFractionDigits: 2 })}
                </span>
              )}
            </span>
          </div>
        );
      })}
    </div>
  );
}
