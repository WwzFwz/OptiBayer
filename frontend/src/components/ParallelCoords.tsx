"use client";
// Parallel coordinates (SVG) — banyak dimensi, tiap garis = satu solusi.
// Warna garis mengikuti nilai dimensi pertama (recovery). Hover = highlight.
import { useState } from "react";
import { C } from "@/lib/theme";

export type Dim = { key: string; label: string };

export default function ParallelCoords({ dims, rows, colorKey }: {
  dims: Dim[]; rows: Array<Record<string, number>>; colorKey: string;
}) {
  const [hover, setHover] = useState<number | null>(null);
  const W = 860, H = 300, padX = 60, padY = 30;
  const colX = (i: number) => padX + (i * (W - 2 * padX)) / (dims.length - 1 || 1);

  const ranges = dims.map((d) => {
    const vals = rows.map((r) => r[d.key]);
    return [Math.min(...vals), Math.max(...vals)] as [number, number];
  });
  const y = (i: number, v: number) => {
    const [lo, hi] = ranges[i];
    return padY + (H - 2 * padY) * (1 - (v - lo) / (hi - lo || 1));
  };
  const cVals = rows.map((r) => r[colorKey]);
  const cMin = Math.min(...cVals), cMax = Math.max(...cVals);
  const lineColor = (v: number) => {
    const t = (v - cMin) / (cMax - cMin || 1);
    const c = [205, 226, 251].map((a, k) =>
      Math.round(a + ([13, 54, 107][k] - a) * t));
    return `rgb(${c[0]},${c[1]},${c[2]})`;
  };

  return (
    <svg viewBox={`0 0 ${W} ${H + 20}`} className="w-full" style={{ maxHeight: 320 }}>
      {dims.map((d, i) => (
        <g key={d.key}>
          <line x1={colX(i)} y1={padY} x2={colX(i)} y2={H - padY}
                stroke={C.grid} strokeWidth={1} />
          <text x={colX(i)} y={padY - 8} textAnchor="middle" fill={C.ink2} fontSize={10}>
            {d.label}
          </text>
          <text x={colX(i)} y={H - padY + 14} textAnchor="middle" fill={C.muted} fontSize={9}>
            {ranges[i][0].toFixed(0)}–{ranges[i][1].toFixed(0)}
          </text>
        </g>
      ))}
      {rows.map((r, ri) => {
        const path = dims.map((d, i) =>
          `${i === 0 ? "M" : "L"}${colX(i)},${y(i, r[d.key])}`).join(" ");
        const dim = hover !== null && hover !== ri;
        return (
          <path key={ri} d={path} fill="none"
                stroke={lineColor(r[colorKey])}
                strokeWidth={hover === ri ? 2.5 : 1}
                strokeOpacity={dim ? 0.08 : 0.6}
                onMouseEnter={() => setHover(ri)}
                onMouseLeave={() => setHover(null)} />
        );
      })}
    </svg>
  );
}
