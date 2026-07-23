"use client";
// HexRadar — profil performa 6 metrik dalam satu segi enam (seperti TFT/tracker).
// Operator langsung baca "bentuk" pabrik: makin penuh & seimbang = makin baik.
// Semua metrik dinormalkan ke 0..1 dgn arah "baik = besar" (OPEX/silika/red mud
// dibalik). Isi emas keemasan estetik.
import { C } from "@/lib/theme";

export type HexMetric = {
  label: string; value: number; norm: number; // norm 0..1, sudah searah "baik"
  grade: string; // S+/S/A/B... utk badge
};

const GOLD = "#c9a24a";
const GOLD_LT = "#e6c063";

export default function HexRadar({ metrics }: { metrics: HexMetric[] }) {
  const N = metrics.length;
  // viewBox lebih lebar dari tinggi supaya label kiri/kanan tidak terpotong
  const cx = 210, cy = 150, R = 105;
  const ang = (i: number) => -Math.PI / 2 + (i * 2 * Math.PI) / N;
  const pt = (i: number, r: number) =>
    [cx + r * Math.cos(ang(i)), cy + r * Math.sin(ang(i))] as const;

  const rings = [0.25, 0.5, 0.75, 1];
  const gridPoly = (f: number) =>
    metrics.map((_, i) => pt(i, R * f).join(",")).join(" ");
  const dataPoly = metrics.map((m, i) =>
    pt(i, R * Math.max(m.norm, 0.04)).join(",")).join(" ");

  return (
    <svg viewBox="0 0 420 300" className="mx-auto w-full" style={{ maxWidth: 460 }}>
      {/* cincin grid heksagonal */}
      {rings.map((f, i) => (
        <polygon key={i} points={gridPoly(f)} fill="none"
                 stroke={C.grid} strokeWidth={1} />
      ))}
      {metrics.map((_, i) => {
        const [x, y] = pt(i, R);
        return <line key={i} x1={cx} y1={cy} x2={x} y2={y} stroke={C.grid} strokeWidth={0.8} />;
      })}
      {/* area data — emas keemasan */}
      <polygon points={dataPoly} fill={GOLD} fillOpacity={0.28}
               stroke={GOLD_LT} strokeWidth={2} strokeLinejoin="round" />
      {metrics.map((m, i) => {
        const [x, y] = pt(i, R * Math.max(m.norm, 0.04));
        return <circle key={i} cx={x} cy={y} r={3} fill={GOLD_LT} />;
      })}
      {/* label + badge grade di ujung tiap sumbu */}
      {metrics.map((m, i) => {
        const [lx, ly] = pt(i, R + 26);
        const anchor = Math.abs(Math.cos(ang(i))) < 0.3 ? "middle"
          : Math.cos(ang(i)) > 0 ? "start" : "end";
        return (
          <g key={i}>
            <circle cx={pt(i, R + 14)[0]} cy={pt(i, R + 14)[1]} r={9}
                    fill="#2a1f12" stroke={GOLD} strokeWidth={1} />
            <text x={pt(i, R + 14)[0]} y={pt(i, R + 14)[1] + 3.5} textAnchor="middle"
                  fill={GOLD_LT} fontSize={9} fontWeight={800}>{m.grade}</text>
            <text x={lx} y={ly + 3} textAnchor={anchor} fill={C.ink2} fontSize={10}>
              {m.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

// grade dari norm 0..1 — selaras zona alarm (good≈0.55–1, warning=0.35, crit=0.12):
// jadi warning selalu ≤C, critical selalu D. Mustahil "sehat" saat alarm merah.
export function grade(norm: number): string {
  if (norm >= 0.92) return "S+";
  if (norm >= 0.82) return "S";
  if (norm >= 0.62) return "A";
  if (norm >= 0.45) return "B";
  if (norm >= 0.28) return "C";
  return "D";
}
