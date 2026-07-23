"use client";
// Korelasi & Scatter — analisis data historis penuh (port dari Overview
// Streamlit sub-tab). Bar korelasi fitur↔target (diverging) + scatter interaktif.
import { useEffect, useState } from "react";
import {
  Bar, BarChart, Cell, ResponsiveContainer, Scatter, ScatterChart,
  Tooltip, XAxis, YAxis, ZAxis,
} from "recharts";
import { CorrelationData, getCorrelation } from "@/lib/api";
import { C } from "@/lib/theme";

export default function CorrelationPanel() {
  const [target, setTarget] = useState("recovery_pct");
  const [feature, setFeature] = useState("reactive_sio2_pct");
  const [d, setD] = useState<CorrelationData | null>(null);

  useEffect(() => {
    let alive = true;
    getCorrelation(target, feature).then((r) => alive && setD(r)).catch(() => {});
    return () => { alive = false; };
  }, [target, feature]);

  // warna diverging: merah (r<0) ↔ biru (r>0)
  const barColor = (r: number) => {
    const t = (r + 1) / 2; // 0..1
    const mix = (a: number[], b: number[]) =>
      a.map((v, i) => Math.round(v + (b[i] - v) * t));
    const c = mix([208, 59, 59], [57, 135, 229]);
    return `rgb(${c[0]},${c[1]},${c[2]})`;
  };

  return (
    <div className="rounded-xl p-3" style={{ background: C.surface, border: `1px solid ${C.grid}` }}>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <p className="text-sm font-semibold" style={{ color: C.ink }}>
          Korelasi & Scatter — input vs target (data historis penuh)
        </p>
        <select value={target} onChange={(e) => setTarget(e.target.value)}
          className="ml-auto rounded px-2 py-1 text-xs"
          style={{ background: C.page, color: C.ink, border: `1px solid ${C.grid}` }}>
          {d?.targets.map((t) => <option key={t.key} value={t.key}>{t.label}</option>)}
        </select>
      </div>
      {!d ? <p className="text-sm" style={{ color: C.muted }}>Memuat…</p> : (
        <div className="grid gap-3 lg:grid-cols-2">
          {/* bar korelasi */}
          <div>
            <ResponsiveContainer width="100%" height={320}>
              <BarChart layout="vertical" data={d.corr}
                margin={{ left: 10, right: 20 }}>
                <XAxis type="number" domain={[-1, 1]} stroke={C.muted} fontSize={11} />
                <YAxis type="category" dataKey="label" width={130}
                       stroke={C.muted} fontSize={10} />
                <Tooltip contentStyle={{ background: C.page, border: `1px solid ${C.grid}`, borderRadius: 8 }}
                         formatter={(v) => [`r = ${v}`, "korelasi"]} />
                <Bar dataKey="r">
                  {d.corr.map((c, i) => <Cell key={i} fill={barColor(c.r)} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            <p className="text-xs" style={{ color: C.muted }}>
              r mendekati −1/+1 = pengaruh kuat. Silika reaktif dominan negatif
              (model belajar kimia yang benar).
            </p>
          </div>
          {/* scatter satu fitur */}
          <div>
            <select value={feature} onChange={(e) => setFeature(e.target.value)}
              className="mb-2 rounded px-2 py-1 text-xs"
              style={{ background: C.page, color: C.ink, border: `1px solid ${C.grid}` }}>
              {d.features.map((f) => <option key={f.key} value={f.key}>{f.label}</option>)}
            </select>
            <ResponsiveContainer width="100%" height={290}>
              <ScatterChart margin={{ top: 5, right: 10, bottom: 20, left: 0 }}>
                <XAxis type="number" dataKey="x" name={d.feature_label}
                       stroke={C.muted} fontSize={11}
                       label={{ value: d.feature_label, position: "insideBottom", offset: -8, fill: C.muted, fontSize: 10 }} />
                <YAxis type="number" dataKey="y" name={d.target_label}
                       stroke={C.muted} fontSize={11} domain={["auto", "auto"]} />
                <ZAxis range={[18, 18]} />
                <Tooltip contentStyle={{ background: C.page, border: `1px solid ${C.grid}`, borderRadius: 8 }} />
                <Scatter data={d.scatter} fill={C.series[0]} fillOpacity={0.4} />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}
