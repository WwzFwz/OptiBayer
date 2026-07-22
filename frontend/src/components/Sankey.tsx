"use client";
// Sankey sederhana (SVG) — sumber → target dengan lebar pita proporsional.
// Cukup untuk neraca Na/Al kita (level tunggal, node kiri→kanan).
import { C } from "@/lib/theme";

export type Flow = { from: string; to: string; value: number; color: string };
export type Node = { id: string; label: string; x: number; col: number };

export default function Sankey({ nodes, flows, height = 320 }: {
  nodes: Node[]; flows: Flow[]; height?: number;
}) {
  const cols = Math.max(...nodes.map((n) => n.col)) + 1;
  const W = 1180;
  // beri margin kanan lebih besar utk label node terminal
  const colX = (c: number) => 40 + (c * (W - 240)) / (cols - 1 || 1);
  // total nilai per node utk tinggi
  const nodeVal: Record<string, number> = {};
  for (const f of flows) {
    nodeVal[f.from] = (nodeVal[f.from] ?? 0) + f.value;
    nodeVal[f.to] = (nodeVal[f.to] ?? 0) + f.value;
  }
  // skala: kolom terpadat (jumlah nilai node + gap) mengisi ~85% tinggi
  const colSum: Record<number, number> = {};
  const colCount: Record<number, number> = {};
  for (const n of nodes) {
    colSum[n.col] = (colSum[n.col] ?? 0) + (nodeVal[n.id] ?? 0);
    colCount[n.col] = (colCount[n.col] ?? 0) + 1;
  }
  let scale = 1;
  for (const c of Object.keys(colSum).map(Number)) {
    const avail = (height - 40) * 0.85 - colCount[c] * 12;
    scale = Math.min(scale, avail / Math.max(colSum[c], 1));
  }
  // posisi Y per node (tumpuk dalam kolom)
  const colStack: Record<number, number> = {};
  const pos: Record<string, { x: number; y: number; h: number }> = {};
  for (const n of nodes) {
    const h = Math.max((nodeVal[n.id] ?? 0) * scale, 16);
    const y = 20 + (colStack[n.col] ?? 0);
    colStack[n.col] = (colStack[n.col] ?? 0) + h + 12;
    pos[n.id] = { x: colX(n.col), y, h };
  }
  // offset link per node
  const outOff: Record<string, number> = {};
  const inOff: Record<string, number> = {};

  return (
    <svg viewBox={`0 0 ${W} ${height}`} className="w-full" style={{ maxHeight: height }}>
      {flows.map((f, i) => {
        const s = pos[f.from], t = pos[f.to];
        if (!s || !t) return null;
        const w = Math.max(f.value * scale, 2);
        const sy = s.y + (outOff[f.from] ?? 0) + w / 2;
        const ty = t.y + (inOff[f.to] ?? 0) + w / 2;
        outOff[f.from] = (outOff[f.from] ?? 0) + w;
        inOff[f.to] = (inOff[f.to] ?? 0) + w;
        const x1 = s.x + 12, x2 = t.x - 2;
        const mx = (x1 + x2) / 2;
        return (
          <path key={i} d={`M${x1},${sy} C${mx},${sy} ${mx},${ty} ${x2},${ty}`}
                fill="none" stroke={f.color} strokeWidth={w} strokeOpacity={0.4} />
        );
      })}
      {nodes.map((n) => {
        const p = pos[n.id];
        return (
          <g key={n.id}>
            <rect x={p.x} y={p.y} width={12} height={p.h} rx={2} fill={C.ink2} />
            <text x={n.col < cols - 1 ? p.x + 18 : p.x - 6} y={p.y + p.h / 2 + 4}
                  textAnchor={n.col < cols - 1 ? "start" : "end"}
                  fill={C.ink2} fontSize={11}>{n.label}</text>
          </g>
        );
      })}
    </svg>
  );
}
