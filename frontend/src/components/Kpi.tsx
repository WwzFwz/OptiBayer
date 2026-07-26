"use client";
// Baris KPI — stat tiles seragam, delta semantik (naik-nya OPEX = merah).
import { useStore } from "@/lib/store";
import { C, INVERTED, statusOf } from "@/lib/theme";
import CountUp from "./ui/CountUp";
import { IntervalBadge, TrustBar } from "./ui/Trust";

// `presisi` = jumlah desimal saat menampilkan lebar interval konformal, biar
// sepadan dengan format angka utamanya (OPEX bulat, CO2 dua desimal, dst).
const TILES = [
  { key: "recovery_pct", label: "Recovery Al", fmt: (v: number) => `${v.toFixed(1)}%`, presisi: 2 },
  { key: "total_opex", label: "OPEX / jam", fmt: (v: number) => v.toLocaleString("id-ID", { maximumFractionDigits: 0 }), presisi: 0 },
  { key: "reactive_sio2_pct", label: "Silika Reaktif", fmt: (v: number) => `${v.toFixed(1)}%`, presisi: 2 },
  { key: "red_mud_t", label: "Red Mud", fmt: (v: number) => `${v.toFixed(1)} t`, presisi: 1 },
  { key: "co2_capture_t", label: "Potensi CO₂", fmt: (v: number) => `${v.toFixed(2)} t`, presisi: 2 },
  { key: "precip_yield_pct", label: "Yield Presipitasi", fmt: (v: number) => `${v.toFixed(1)}%`, presisi: 2 },
] as const;

export default function Kpi() {
  const { hourData, seq, hour } = useStore();
  if (!hourData) return <div className="h-24" />;
  const prev = hour > 0 ? seq?.hours[hour - 1] : undefined;

  return (
    <>
    <TrustBar ood={hourData.ood} physics={hourData.physics_check} className="mb-2" />
    <div className="grid grid-cols-2 gap-2 md:grid-cols-3 xl:grid-cols-6">
      {TILES.map(({ key, label, fmt, presisi }) => {
        const v = hourData.kpi[key as keyof typeof hourData.kpi];
        const iv = hourData.interval?.[key];
        const st = statusOf(key, v);
        const pv = prev?.[key as keyof typeof prev] as number | undefined;
        const delta = pv !== undefined && key !== "co2_capture_t" ? v - pv : undefined;
        const improving = delta !== undefined &&
          (INVERTED.has(key) ? delta < 0 : delta > 0);
        return (
          <div key={key}
               className="flex min-h-[7.2rem] flex-col items-center justify-center rounded-xl p-3 text-center"
               style={{ background: C.surface, border: `1px solid ${C.grid}` }}>
            <p className="mb-1 flex items-center gap-1 text-[0.68rem] font-semibold uppercase tracking-wider"
               style={{ color: C.muted }}>
              <span style={{ color: C.status[st], fontSize: "0.6rem" }}>●</span>
              {label}
            </p>
            <p className="text-2xl font-bold" style={{ color: C.ink }}>
              <CountUp value={v} format={fmt} />
            </p>
            {/* lebar ketidakpastian model, kalau target ini memang diprediksi */}
            <IntervalBadge interval={iv} digits={presisi} />
            {delta !== undefined ? (
              <p className="mt-1 rounded-full px-2 py-0.5 text-xs font-semibold"
                 style={{
                   background: improving ? "#0ca30c22" : "#d03b3b22",
                   color: improving ? C.status.good : C.status.critical,
                 }}>
                {delta >= 0 ? "↑" : "↓"} {Math.abs(delta).toFixed(1)}
              </p>
            ) : <p className="mt-1 h-5" />}
          </div>
        );
      })}
    </div>
    </>
  );
}
