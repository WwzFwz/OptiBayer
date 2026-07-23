"use client";
// What-if Digesti — geser 5 setpoint utk feed jam ini, prediksi live (port
// dari app/views/digestion.py). Komposisi terkunci pada jam replay aktif.
import { useEffect, useState } from "react";
import { OperatingMap, postOp } from "@/lib/api";
import { C } from "@/lib/theme";

const KNOBS = [
  ["particle_size_um", "Ukuran Partikel"], ["digester_temp_c", "Suhu Digester"],
  ["naoh_conc_gl", "Konsentrasi NaOH"], ["precip_temp_c", "Suhu Presipitasi"],
  ["seed_ratio", "Rasio Seed"],
] as const;
const TARGETS = [
  ["recovery_pct", "Recovery", "%"], ["total_opex", "OPEX/jam", ""],
  ["red_mud_t", "Red Mud", "t"], ["precip_yield_pct", "Yield", "%"],
] as const;

export default function WhatIfDigesti({ map }: { map: OperatingMap }) {
  const [knobs, setKnobs] = useState<Record<string, number>>(map.knobs_now);
  const [pred, setPred] = useState<Record<string, number> | null>(null);
  const base = map.knobs_now;

  useEffect(() => { setKnobs(map.knobs_now); }, [map]);

  useEffect(() => {
    let alive = true;
    postOp("predict", { composition: map.composition, knobs })
      .then((r) => alive && setPred(r.result)).catch(() => {});
    return () => { alive = false; };
  }, [knobs, map]);

  // prediksi baseline (setpoint jam ini) untuk menghitung delta
  const [b, setB] = useState<Record<string, number> | null>(null);
  useEffect(() => {
    postOp("predict", { composition: map.composition, knobs: map.knobs_now })
      .then((r) => setB(r.result)).catch(() => {});
  }, [map]);

  return (
    <div className="rounded-xl p-3" style={{ background: C.surface, border: `1px solid ${C.grid}` }}>
      <p className="mb-1 text-sm font-semibold" style={{ color: C.ink }}>
        What-if cepat — setpoint untuk feed JAM INI
      </p>
      <p className="mb-3 text-xs" style={{ color: C.muted }}>
        Komposisi terkunci pada jam replay aktif. Untuk eksperimen bebas
        (ubah komposisi & feed rate), pakai Prediction Lab.
      </p>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        {KNOBS.map(([k, lbl]) => {
          const [lo, hi] = map.bounds[k];
          return (
            <div key={k}>
              <label className="text-xs" style={{ color: C.ink2 }}>{lbl}: {knobs[k]?.toFixed(1)}</label>
              <input type="range" min={lo} max={hi} step={(hi - lo) / 100}
                     value={knobs[k]} className="w-full"
                     onChange={(e) => setKnobs({ ...knobs, [k]: Number(e.target.value) })} />
            </div>
          );
        })}
      </div>
      {pred && (
        <div className="mt-3 grid grid-cols-2 gap-2 md:grid-cols-4">
          {TARGETS.map(([k, lbl, u]) => {
            const v = pred[k], bv = b?.[k];
            const d = bv !== undefined ? v - bv : undefined;
            const goodUp = k === "recovery_pct" || k === "precip_yield_pct";
            const improving = d !== undefined && (goodUp ? d > 0 : d < 0);
            return (
              <div key={k} className="rounded-lg p-2 text-center"
                   style={{ background: C.page, border: `1px solid ${C.grid}` }}>
                <p className="text-xs" style={{ color: C.muted }}>{lbl}</p>
                <p className="text-base font-bold" style={{ color: C.ink }}>
                  {v?.toLocaleString("id-ID", { maximumFractionDigits: 1 })} {u}
                </p>
                {d !== undefined && Math.abs(d) > 0.01 && (
                  <p className="text-xs font-semibold"
                     style={{ color: improving ? C.status.good : C.status.critical }}>
                    {d >= 0 ? "↑" : "↓"} {Math.abs(d).toLocaleString("id-ID", { maximumFractionDigits: 1 })}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      )}
      <button onClick={() => setKnobs(base)}
        className="mt-2 rounded px-3 py-1 text-xs"
        style={{ border: `1px solid ${C.grid}`, color: C.ink2 }}>
        Reset ke setpoint jam ini
      </button>
    </div>
  );
}
