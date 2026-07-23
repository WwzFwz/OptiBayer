"use client";
// Digesti — heatmap operating map (recovery = f(T×NaOH)) + Pareto scatter + radar.
import { useEffect, useState } from "react";
import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, ResponsiveContainer,
  ScatterChart, Scatter, XAxis, YAxis, ZAxis, Tooltip, Cell,
} from "recharts";
import { getOperatingMap, getPareto, OperatingMap, ParetoData } from "@/lib/api";
import ParallelCoords, { Dim } from "@/components/ParallelCoords";
import ExplainAI from "@/components/ExplainAI";
import WhatIfDigesti from "@/components/WhatIfDigesti";
import { useStore } from "@/lib/store";
import { C } from "@/lib/theme";

// interpolasi sekuensial biru (mirip SEQ_BLUE)
function blue(t: number): string {
  const stops = [[205, 226, 251], [57, 135, 229], [13, 54, 107]];
  const i = t < 0.5 ? 0 : 1;
  const f = t < 0.5 ? t * 2 : (t - 0.5) * 2;
  const [a, b] = [stops[i], stops[i + 1]];
  const c = a.map((v, k) => Math.round(v + (b[k] - v) * f));
  return `rgb(${c[0]},${c[1]},${c[2]})`;
}

export default function Digesti() {
  const { scenario, hour } = useStore();
  const [map, setMap] = useState<OperatingMap | null>(null);
  const [pf, setPf] = useState<ParetoData | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let alive = true;
    getOperatingMap(scenario, hour).then((d) => alive && setMap(d)).catch(() => {});
    return () => { alive = false; };
  }, [scenario, hour]);

  async function runPareto() {
    setLoading(true);
    try { setPf(await getPareto(scenario, hour)); } finally { setLoading(false); }
  }

  const zmin = map ? Math.min(...map.z.flat()) : 0;
  const zmax = map ? Math.max(...map.z.flat()) : 1;

  return (
    <div className="space-y-3">
      {/* Operating map heatmap */}
      <div className="rounded-xl p-3" style={{ background: C.surface, border: `1px solid ${C.grid}` }}>
        <p className="mb-2 text-sm font-semibold" style={{ color: C.ink }}>
          Peta Operasi — Recovery = f(Suhu Digester × NaOH)
        </p>
        {!map ? <p style={{ color: C.muted }}>Memuat peta…</p> : (
          <div className="overflow-x-auto">
            <svg viewBox={`0 0 ${map.temps.length * 26 + 60} ${map.naohs.length * 20 + 40}`}
                 className="w-full" style={{ maxHeight: 420 }}>
              {map.z.map((rowv, r) =>
                rowv.map((v, c) => (
                  <rect key={`${r}-${c}`} x={c * 26 + 50}
                        y={(map.naohs.length - 1 - r) * 20 + 10}
                        width={25} height={19}
                        fill={blue((v - zmin) / (zmax - zmin || 1))} />
                ))
              )}
              {/* marker posisi sekarang (✕) & rekomendasi (★) */}
              {(() => {
                const cell = (t: number, naoh: number) => {
                  const ci = map.temps.reduce((b, v, i) =>
                    Math.abs(v - t) < Math.abs(map.temps[b] - t) ? i : b, 0);
                  const ri = map.naohs.reduce((b, v, i) =>
                    Math.abs(v - naoh) < Math.abs(map.naohs[b] - naoh) ? i : b, 0);
                  return { x: ci * 26 + 62, y: (map.naohs.length - 1 - ri) * 20 + 22 };
                };
                const now = cell(map.now.t, map.now.naoh);
                const rec = cell(map.reco.t, map.reco.naoh);
                return (<>
                  <text x={now.x} y={now.y} textAnchor="middle" fill={C.ink}
                        fontSize={15} fontWeight={900}>✕</text>
                  <text x={rec.x} y={rec.y} textAnchor="middle" fill={C.status.good}
                        fontSize={16} fontWeight={900}>★</text>
                </>);
              })()}
              <text x={map.temps.length * 13 + 50} y={map.naohs.length * 20 + 34}
                    textAnchor="middle" fill={C.muted} fontSize={11}>Suhu Digester (°C) →</text>
            </svg>
            <div className="flex items-center gap-4 text-xs" style={{ color: C.muted }}>
              <span><b style={{ color: C.ink }}>✕</b> operasi sekarang</span>
              <span><b style={{ color: C.status.good }}>★</b> rekomendasi optimizer</span>
              <span className="flex items-center gap-1">
                recovery {zmin.toFixed(0)}
                <span style={{ display: "inline-block", width: 60, height: 8,
                  background: `linear-gradient(90deg, ${blue(0)}, ${blue(1)})`, borderRadius: 2 }} />
                {zmax.toFixed(0)}%
              </span>
            </div>
          </div>
        )}
      </div>

      {/* What-if setpoint jam ini */}
      {map && <WhatIfDigesti map={map} />}

      {/* Pareto + radar */}
      <div className="rounded-xl p-3" style={{ background: C.surface, border: `1px solid ${C.grid}` }}>
        <div className="mb-2 flex items-center justify-between">
          <p className="text-sm font-semibold" style={{ color: C.ink }}>
            Kurva Pareto (carbon-aware) & Radar Setpoint
          </p>
          <button onClick={runPareto} disabled={loading}
            className="btn-lift rounded-lg px-3 py-1.5 text-sm font-semibold"
            style={{ background: C.accent, color: "#1a1408", opacity: loading ? 0.6 : 1 }}>
            {loading ? "Menghitung…" : "Hitung Pareto"}
          </button>
        </div>
        {!pf ? (
          <p className="text-sm" style={{ color: C.muted }}>
            Klik "Hitung Pareto" untuk optimasi NSGA-II pada komposisi jam ini.
          </p>
        ) : (
          <div className="grid gap-3 lg:grid-cols-2">
            <ResponsiveContainer width="100%" height={280}>
              <ScatterChart margin={{ top: 10, right: 10, bottom: 20, left: 0 }}>
                <XAxis type="number" dataKey="net_opex" name="Net OPEX"
                       stroke={C.muted} fontSize={11}
                       tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
                       label={{ value: "Net OPEX", position: "insideBottom", offset: -8, fill: C.muted, fontSize: 11 }} />
                <YAxis type="number" dataKey="recovery_pct" name="Recovery"
                       stroke={C.muted} fontSize={11} domain={["auto", "auto"]} />
                <ZAxis range={[50, 50]} />
                <Tooltip contentStyle={{ background: C.page, border: `1px solid ${C.grid}`, borderRadius: 8 }}
                         formatter={(v) => (typeof v === "number" ? v.toFixed(1) : String(v))} />
                <Scatter data={pf.solutions} fill={C.series[0]}>
                  {pf.solutions.map((_, i) => <Cell key={i} fill={C.series[0]} fillOpacity={0.55} />)}
                </Scatter>
                <Scatter data={[pf.picked]} fill={C.status.good} shape="star" />
              </ScatterChart>
            </ResponsiveContainer>
            <ResponsiveContainer width="100%" height={280}>
              <RadarChart data={Object.keys(pf.labels).map((k) => {
                const [lo, hi] = pf.bounds[k];
                const norm = (v: number) => (v - lo) / (hi - lo || 1);
                return { axis: pf.labels[k].split(" ")[0],
                         Sekarang: norm(pf.now_knobs[k]),
                         Rekomendasi: norm(pf.picked[k]) };
              })}>
                <PolarGrid stroke={C.grid} />
                <PolarAngleAxis dataKey="axis" tick={{ fill: C.ink2, fontSize: 10 }} />
                <Radar name="Sekarang" dataKey="Sekarang" stroke={C.series[0]}
                       fill={C.series[0]} fillOpacity={0.15} />
                <Radar name="Rekomendasi" dataKey="Rekomendasi" stroke={C.status.good}
                       fill={C.status.good} fillOpacity={0.12} />
                <Tooltip contentStyle={{ background: C.page, border: `1px solid ${C.grid}`, borderRadius: 8 }} />
              </RadarChart>
            </ResponsiveContainer>
            {/* Parallel coordinates — eksplorasi trade-off multi-dimensi */}
            <div className="lg:col-span-2">
              <p className="mb-1 text-xs font-semibold" style={{ color: C.ink2 }}>
                Parallel Coordinates — tiap garis = satu solusi Pareto (hover untuk sorot)
              </p>
              <ParallelCoords colorKey="recovery_pct" rows={pf.solutions}
                dims={([
                  ...Object.keys(pf.labels).map((k) => ({ key: k, label: pf.labels[k].split(" ")[0] })),
                  { key: "recovery_pct", label: "Recovery" },
                  { key: "net_opex", label: "Net OPEX" },
                  { key: "red_mud_t", label: "Red Mud" },
                ] as Dim[])} />
            </div>
          </div>
        )}
        <ExplainAI title="Peta Operasi Digesti"
          tags={["silika", "digesti", "opmap", "advisory"]}
          context={{
            posisi_sekarang: map?.now,
            rekomendasi: pf?.picked,
            recovery_range: map ? [zmin, zmax] : undefined,
          }} />
      </div>
    </div>
  );
}
