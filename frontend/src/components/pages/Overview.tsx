"use client";
// Overview — 4 tren + pita alarm + regret meter + handover + Analisis AI.
import { useState } from "react";
import {
  Area, Line, LineChart, ComposedChart, ReferenceArea, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { getRegret, RegretData } from "@/lib/api";
import ExplainAI from "@/components/ExplainAI";
import HexRadar, { grade, HexMetric } from "@/components/HexRadar";
import { useStore } from "@/lib/store";
import { C } from "@/lib/theme";

// normalisasi tiap KPI ke 0..1 searah "baik = penuh" (clamp ke rentang wajar)
function healthMetrics(kpi: Record<string, number>): HexMetric[] {
  const norm = (v: number, lo: number, hi: number, invert = false) => {
    const t = Math.max(0, Math.min(1, (v - lo) / (hi - lo)));
    return invert ? 1 - t : t;
  };
  const rows: Array<[string, number]> = [
    ["Recovery", norm(kpi.recovery_pct, 80, 97)],
    ["Efisiensi Biaya", norm(kpi.total_opex, 15000, 45000, true)],
    ["Silika Bersih", norm(kpi.reactive_sio2_pct, 2, 8, true)],
    ["Minim Red Mud", norm(kpi.red_mud_t, 240, 640, true)],
    ["Potensi CO₂", norm(kpi.co2_capture_t, 5, 16)],
    ["Yield", norm(kpi.precip_yield_pct, 72, 82)],
  ];
  return rows.map(([label, n]) => ({
    label, value: n, norm: n, grade: grade(n),
  }));
}

const CHARTS = [
  { key: "recovery_pct", title: "Recovery Al (%)", color: C.series[0], band: [85, 100] },
  { key: "total_opex", title: "Total OPEX (/jam)", color: C.series[2], band: [0, 25000] },
  { key: "reactive_sio2_pct", title: "Silika Reaktif Feed (%) — musuh utama", color: C.series[4], band: [0, 5.5] },
  { key: "red_mud_t", title: "Red Mud Basah (t)", color: C.series[1], band: [0, 500] },
] as const;

export default function Overview() {
  const { seq, hour, setHour, scenario, hourData } = useStore();
  const [rg, setRg] = useState<RegretData | null>(null);
  const [busy, setBusy] = useState(false);

  if (!seq) return <p style={{ color: C.muted }}>Memuat deret replay…</p>;
  const data = seq.hours.map((h, i) => ({ jam: i, ...h }));

  async function runRegret() {
    setBusy(true);
    try { setRg(await getRegret(scenario, hour)); } finally { setBusy(false); }
  }

  const health = hourData ? healthMetrics(hourData.kpi as Record<string, number>) : null;
  const avgGrade = health
    ? (health.reduce((a, m) => a + m.norm, 0) / health.length) : 0;

  return (
    <div className="space-y-3">
    {/* Profil Kesehatan Pabrik — hexagon radar */}
    {health && (
      <div className="grid gap-3 lg:grid-cols-3">
        <div className="rounded-xl p-3" style={{ background: C.surface, border: `1px solid ${C.grid}` }}>
          <p className="mb-1 text-sm font-semibold" style={{ color: C.ink }}>
            Profil Kesehatan Pabrik
          </p>
          <p className="mb-2 text-xs" style={{ color: C.muted }}>
            Skor jam ini · <b style={{ color: "#e6c063" }}>{grade(avgGrade)}</b> —
            makin penuh & seimbang segi enamnya, makin sehat.
          </p>
          <HexRadar metrics={health} />
        </div>
        <div className="lg:col-span-2 grid grid-cols-2 gap-2 md:grid-cols-3">
          {health.map((m) => (
            <div key={m.label} className="flex flex-col justify-center rounded-lg p-3"
                 style={{ background: C.page, border: `1px solid ${C.grid}` }}>
              <div className="flex items-center justify-between">
                <span className="text-xs" style={{ color: C.muted }}>{m.label}</span>
                <span className="grid h-6 w-6 place-items-center rounded-full text-xs font-extrabold"
                      style={{ background: "#2a1f12", color: "#e6c063",
                               border: "1px solid #c9a24a" }}>{m.grade}</span>
              </div>
              <div className="mt-2 h-1.5 w-full rounded-full" style={{ background: C.grid }}>
                <div className="h-full rounded-full"
                     style={{ width: `${m.norm * 100}%`, background: "#c9a24a" }} />
              </div>
            </div>
          ))}
        </div>
      </div>
    )}

    <div className="grid gap-3 lg:grid-cols-2">
      {CHARTS.map(({ key, title, color, band }) => (
        <div key={key} className="rounded-xl p-3"
             style={{ background: C.surface, border: `1px solid ${C.grid}` }}>
          <p className="mb-2 text-sm font-semibold" style={{ color: C.ink }}>{title}</p>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={data}
                       onClick={(e) => e?.activeLabel !== undefined && setHour(Number(e.activeLabel))}>
              <XAxis dataKey="jam" stroke={C.muted} fontSize={11}
                     tickLine={false} axisLine={{ stroke: C.grid }} />
              <YAxis stroke={C.muted} fontSize={11} width={48}
                     tickLine={false} axisLine={{ stroke: C.grid }}
                     domain={["auto", "auto"]}
                     tickFormatter={(v: number) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : `${v}`} />
              <Tooltip
                contentStyle={{ background: C.page, border: `1px solid ${C.grid}`, borderRadius: 8 }}
                labelStyle={{ color: C.muted }} itemStyle={{ color }}
                formatter={(v) => [Number(v).toFixed(2), title]}
                labelFormatter={(l) => `Jam ${l}:00`} />
              <ReferenceArea y1={band[0]} y2={band[1]}
                             fill="#ffffff" fillOpacity={0.04}
                             stroke={C.muted} strokeOpacity={0.25} strokeDasharray="4 4" />
              <ReferenceLine x={hour} stroke={C.ink} strokeDasharray="4 3" />
              <Line type="monotone" dataKey={key} stroke={color}
                    strokeWidth={2} dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      ))}
      <p className="text-xs lg:col-span-2" style={{ color: C.muted }}>
        Pita transparan = zona operasi aman · garis putus-putus = jam aktif ·
        klik pada chart untuk melompat ke jam tersebut.
      </p>
    </div>

    {/* Analisis AI untuk kondisi jam aktif */}
    {hourData && (
      <ExplainAI title="Kondisi Operasi (jam aktif)"
        tags={["silika", "digesti", "advisory"]}
        context={{
          silika_reaktif_pct: hourData.kpi.reactive_sio2_pct,
          recovery_pct: hourData.kpi.recovery_pct,
          total_opex: hourData.kpi.total_opex,
          red_mud_t: hourData.kpi.red_mud_t,
          silika_level: hourData.silika_level,
          rekomendasi: hourData.recommended_knobs,
          delta_jika_diikuti: hourData.delta_if_followed,
        }} />
    )}

    {/* Regret meter + counterfactual + handover */}
    <div className="rounded-xl p-3" style={{ background: C.surface, border: `1px solid ${C.grid}` }}>
      <div className="mb-2 flex items-center justify-between">
        <p className="text-sm font-semibold" style={{ color: C.ink }}>
          Regret Meter — nilai yang tertinggal (8 jam terakhir)
        </p>
        <button onClick={runRegret} disabled={busy}
          className="rounded px-3 py-1.5 text-sm font-semibold"
          style={{ background: C.series[0], color: "#fff", opacity: busy ? 0.6 : 1 }}>
          {busy ? "Menghitung…" : "Hitung Regret + Laporan"}
        </button>
      </div>
      {!rg ? (
        <p className="text-sm" style={{ color: C.muted }}>
          Counterfactual: seandainya setpoint 8 jam terakhir mengikuti advisory —
          berapa recovery/OPEX yang tidak hilang.
        </p>
      ) : (
        <div className="grid gap-3 lg:grid-cols-2">
          <div>
            <div className="grid grid-cols-3 gap-2">
              <Metric label="Δ Recovery" val={`${rg.delta.recovery_pct >= 0 ? "+" : ""}${rg.delta.recovery_pct.toFixed(2)}%`} good={rg.delta.recovery_pct > 0} />
              <Metric label="Δ OPEX (8 jam)" val={`${rg.delta.total_opex >= 0 ? "+" : ""}${rg.delta.total_opex.toLocaleString("id-ID", { maximumFractionDigits: 0 })}`} good={rg.delta.total_opex < 0} />
              <Metric label="Δ Red Mud" val={`${rg.delta.red_mud_t >= 0 ? "+" : ""}${rg.delta.red_mud_t.toFixed(1)} t`} good={rg.delta.red_mud_t < 0} />
            </div>
            <ResponsiveContainer width="100%" height={200}>
              <ComposedChart data={rg.series}>
                <XAxis dataKey="sim_hour" stroke={C.muted} fontSize={11} />
                <YAxis stroke={C.muted} fontSize={11} domain={["auto", "auto"]} />
                <Tooltip contentStyle={{ background: C.page, border: `1px solid ${C.grid}`, borderRadius: 8 }} />
                <Area type="monotone" dataKey="counterfactual" stroke={C.status.good}
                      strokeDasharray="5 3" fill={C.status.good} fillOpacity={0.14}
                      name="Jika advisory diikuti" isAnimationActive={false} />
                <Line type="monotone" dataKey="actual" stroke={C.series[0]}
                      strokeWidth={2} dot={false} name="Aktual" isAnimationActive={false} />
              </ComposedChart>
            </ResponsiveContainer>
            <p className="text-xs" style={{ color: C.muted }}>
              Area di antara dua garis = regret (nilai yang tertinggal).
            </p>
          </div>
          <div>
            <p className="mb-1 text-sm font-semibold" style={{ color: C.ink }}>
              Laporan Serah Terima Shift
            </p>
            <pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded p-2 text-xs"
                 style={{ background: C.page, color: C.ink2, border: `1px solid ${C.grid}` }}>
              {rg.handover}
            </pre>
            <p className="mt-1 text-xs" style={{ color: C.muted }}>backend: {rg.handover_backend}</p>
          </div>
        </div>
      )}
    </div>
    </div>
  );
}

function Metric({ label, val, good }: { label: string; val: string; good: boolean }) {
  return (
    <div className="rounded-lg p-2 text-center" style={{ background: C.page, border: `1px solid ${C.grid}` }}>
      <p className="text-xs" style={{ color: C.muted }}>{label}</p>
      <p className="text-base font-bold" style={{ color: good ? C.status.good : C.status.critical }}>{val}</p>
    </div>
  );
}
