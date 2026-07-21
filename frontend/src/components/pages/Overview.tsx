"use client";
// Overview — 4 tren + pita alarm + penanda jam aktif (port dari Streamlit).
import {
  Line, LineChart, ReferenceArea, ReferenceLine, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from "recharts";
import { useStore } from "@/lib/store";
import { C } from "@/lib/theme";

const CHARTS = [
  { key: "recovery_pct", title: "Recovery Al (%)", color: C.series[0], band: [85, 100] },
  { key: "total_opex", title: "Total OPEX (/jam)", color: C.series[2], band: [0, 25000] },
  { key: "reactive_sio2_pct", title: "Silika Reaktif Feed (%) — musuh utama", color: C.series[4], band: [0, 5.5] },
  { key: "red_mud_t", title: "Red Mud Basah (t)", color: C.series[1], band: [0, 500] },
] as const;

export default function Overview() {
  const { seq, hour, setHour } = useStore();
  if (!seq) return <p style={{ color: C.muted }}>Memuat deret replay…</p>;

  const data = seq.hours.map((h, i) => ({ jam: i, ...h }));

  return (
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
  );
}
