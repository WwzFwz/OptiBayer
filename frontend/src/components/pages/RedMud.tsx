"use client";
// Red Mud & CCUS — panel karbonasi (kalkulator paper 2026).
import { useState } from "react";
import { useStore } from "@/lib/store";
import { C } from "@/lib/theme";

export default function RedMud() {
  const { hourData } = useStore();
  const [price, setPrice] = useState(30000);
  if (!hourData) return <p style={{ color: C.muted }}>Memuat…</p>;
  const cb = hourData.carbonation;
  const rm = hourData.kpi.red_mud_t;
  const co2 = cb.co2_sequestered_t ?? rm * 0.023;
  const water = cb.water_needed_t ?? rm * 2;
  const value = co2 * price;

  return (
    <div className="space-y-3">
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
