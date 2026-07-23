"use client";
// Red Mud & CCUS — panel karbonasi (kalkulator paper 2026).
import { useState } from "react";
import Sankey, { Flow, Node } from "@/components/Sankey";
import ExplainAI from "@/components/ExplainAI";
import { useStore } from "@/lib/store";
import { C } from "@/lib/theme";

export default function RedMud() {
  const { hourData } = useStore();
  const [price, setPrice] = useState(30000);
  if (!hourData) return <p style={{ color: C.muted }}>Memuat…</p>;
  const cb = hourData.carbonation;
  const ab = hourData.al_balance ?? {};
  const rm = hourData.kpi.red_mud_t;
  const co2 = cb.co2_sequestered_t ?? rm * 0.023;
  const water = cb.water_needed_t ?? rm * 2;
  const value = co2 * price;

  // Sankey aluminium: feed + recycle → produk / hilang ke red mud
  const feed = ab.feed_t ?? 0, recyc = ab.recycled_t ?? 0;
  const prod = ab.hydrate_t ?? 0, lost = ab.lost_redmud_t ?? 0;
  const alNodes: Node[] = [
    { id: "feed", label: "Al Bauksit", x: 0, col: 0 },
    { id: "recyc", label: "Al Recycle", x: 0, col: 0 },
    { id: "proc", label: "Proses", x: 0, col: 1 },
    { id: "prod", label: "Produk Al(OH)₃", x: 0, col: 2 },
    { id: "lost", label: "Hilang ke Red Mud", x: 0, col: 2 },
  ];
  const alFlows: Flow[] = [
    { from: "feed", to: "proc", value: feed, color: C.series[0] },
    { from: "recyc", to: "proc", value: recyc, color: C.series[4] },
    { from: "proc", to: "prod", value: prod, color: C.status.good },
    { from: "proc", to: "lost", value: lost, color: C.status.critical },
  ];

  return (
    <div className="space-y-3">
      {(feed > 0 || lost > 0) && (
        <div className="rounded-xl p-3" style={{ background: C.surface, border: `1px solid ${C.grid}` }}>
          <p className="mb-2 text-sm font-semibold" style={{ color: C.ink }}>
            Sankey Aluminium — feed → produk / hilang (ton Al/jam)
          </p>
          <Sankey nodes={alNodes} flows={alFlows} height={300} />
          <p className="text-xs" style={{ color: C.muted }}>
            Hilang ke red mud: <b style={{ color: C.status.critical }}>{lost.toFixed(1)} t Al</b>
            {feed > 0 && ` (${(lost / feed * 100).toFixed(1)}% feed)`} — tiap ton
            menaikkan alkalinitas & volume tailing.
          </p>
        </div>
      )}
      <div className="rounded-xl p-3" style={{ background: C.surface, border: `1px solid ${C.grid}` }}>
        <p className="mb-1 text-sm font-semibold" style={{ color: C.ink }}>
          Karbonasi Akuatik Langsung — red mud sebagai sink CO₂
        </p>
        <p className="mb-3 text-xs" style={{ color: C.muted }}>
          Kalkulator deterministik dari paper ScienceDirect 2026
          (2.3 g CO₂/100 g RM · L/S 2:1 · mass loss 14.19% vs 10.74%).
        </p>
        <label className="text-xs" style={{ color: C.ink2 }}>
          Harga karbon (Rp/ton CO₂): {price.toLocaleString("id-ID")}
        </label>
        <input type="range" min={0} max={1400000} step={10000} value={price}
               onChange={(e) => setPrice(Number(e.target.value))}
               className="mb-4 block w-full max-w-md" />
        <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
          <Cell label="Red mud jam ini" val={`${rm.toFixed(1)} t`} />
          <Cell label="CO₂ tersekuestrasi" val={`${co2.toFixed(2)} t`} color={C.status.good} />
          <Cell label="Air (L/S 2:1)" val={`${water.toFixed(0)} t`} />
          <Cell label="Nilai karbon" val={`Rp${value.toLocaleString("id-ID", { maximumFractionDigits: 0 })}`} color={C.status.good} />
        </div>
      </div>
      <div className="rounded-xl p-3" style={{ background: C.surface, border: `1px solid ${C.grid}` }}>
        <p className="text-sm" style={{ color: C.ink2 }}>
          <b style={{ color: C.status.good }}>Status pH tailing (estimasi):</b> pH 11–13
          (di luar baku mutu) → sesudah karbonasi <b>pH 8–9.5</b> → memenuhi pita
          Permen LHK No. 6/2021 (pH 7–10), membuka jalur backfill / produk sirkular
          alih-alih landfill.
        </p>
        <ExplainAI title="Karbonasi CCUS Red Mud"
          tags={["ccus", "redmud", "karbon", "tailing", "esg"]}
          context={{ red_mud_t: rm, co2_tersekuestrasi_t: co2,
            nilai_karbon_rp: value, harga_karbon_rp_per_t: price }} />
      </div>
    </div>
  );
}
function Cell({ label, val, color }: { label: string; val: string; color?: string }) {
  return (
    <div className="rounded-lg p-3" style={{ background: C.page, border: `1px solid ${C.grid}` }}>
      <p className="text-xs" style={{ color: C.muted }}>{label}</p>
      <p className="text-lg font-bold" style={{ color: color ?? C.ink }}>{val}</p>
    </div>
  );
}
