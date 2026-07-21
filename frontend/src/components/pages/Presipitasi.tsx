"use client";
// Presipitasi — kurva Ceq (Misra) + gap supersaturasi.
import { useEffect, useState } from "react";
import {
  Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { CeqData, getCeq } from "@/lib/api";
import { useStore } from "@/lib/store";
import { C } from "@/lib/theme";

export default function Presipitasi() {
  const { hourData } = useStore();
  const [a, setA] = useState(130);
  const [ceq, setCeq] = useState<CeqData | null>(null);
  const caustic = 150;
  const tNow = hourData ? 60 : 60;

  useEffect(() => {
    let alive = true;
    getCeq(a, caustic, tNow).then((d) => alive && setCeq(d)).catch(() => {});
    return () => { alive = false; };
  }, [a, tNow]);

  const data = ceq?.temps.map((t, i) => ({ t, ceq: ceq.ceq[i] })) ?? [];

  return (
    <div className="space-y-3">
      <div className="rounded-xl p-3" style={{ background: C.surface, border: `1px solid ${C.grid}` }}>
        <p className="mb-1 text-sm font-semibold" style={{ color: C.ink }}>
          Kurva Ekuilibrium Gibbsite — gap supersaturasi
        </p>
        <p className="mb-3 text-xs" style={{ color: C.muted }}>
          Gap antara alumina terlarut (A) dan garis Ceq = driving force
          presipitasi = yield yang masih bisa diambil.
        </p>
        <div className="mb-3 flex items-center gap-3">
          <label className="text-xs" style={{ color: C.ink2 }}>Alumina terlarut A: {a} g/L</label>
          <input type="range" min={80} max={180} step={5} value={a}
                 onChange={(e) => setA(Number(e.target.value))} className="flex-1 max-w-xs" />
          {ceq && (
            <span className="rounded-full px-3 py-1 text-xs font-semibold"
                  style={{ background: "#3987e522", color: C.series[0] }}>
              gap {ceq.gap.toFixed(1)} g/L
            </span>
          )}
        </div>
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={data}>
            <XAxis dataKey="t" stroke={C.muted} fontSize={11}
                   label={{ value: "Suhu (°C)", position: "insideBottom", offset: -4, fill: C.muted, fontSize: 11 }} />
            <YAxis stroke={C.muted} fontSize={11}
                   label={{ value: "Al₂O₃ terlarut (g/L)", angle: -90, position: "insideLeft", fill: C.muted, fontSize: 11 }} />
            <Tooltip contentStyle={{ background: C.page, border: `1px solid ${C.grid}`, borderRadius: 8 }} />
            <ReferenceLine y={a} stroke={C.series[2]} strokeDasharray="6 4"
                           label={{ value: `A ≈ ${a}`, fill: C.series[2], fontSize: 11 }} />
            <Line type="monotone" dataKey="ceq" stroke={C.series[0]} strokeWidth={2}
                  dot={false} name="Ceq" isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
