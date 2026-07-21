"use client";
// Liquor Loop — Sankey natrium: ke mana NaOH bocor.
import Sankey, { Flow, Node } from "@/components/Sankey";
import { useStore } from "@/lib/store";
import { C } from "@/lib/theme";

export default function Liquor() {
  const { hourData } = useStore();
  if (!hourData) return <p style={{ color: C.muted }}>Memuat…</p>;
  const nb = hourData.na_balance;
  const mk = Math.max(nb.makeup_t ?? 0, 0.01);

  const nodes: Node[] = [
    { id: "makeup", label: "NaOH Make-up", x: 0, col: 0 },
    { id: "recycle", label: "NaOH Recycle", x: 0, col: 0 },
    { id: "used", label: "NaOH Terpakai", x: 0, col: 1 },
    { id: "dsp", label: "Terkunci DSP (silika)", x: 0, col: 2 },
    { id: "dead", label: "Soda Mati (net)", x: 0, col: 2 },
    { id: "phys", label: "Hilang Fisik (red mud)", x: 0, col: 2 },
    { id: "back", label: "Kembali ke Liquor", x: 0, col: 2 },
  ];
  const back = Math.max((nb.consumed_t ?? 0) - (nb.dsp_loss_t ?? 0) -
    (nb.dead_soda_net_t ?? 0) - (nb.physical_loss_t ?? 0), 0);
  const flows: Flow[] = [
    { from: "makeup", to: "used", value: nb.makeup_t ?? 0, color: C.series[0] },
    { from: "recycle", to: "used", value: nb.recycled_t ?? 0, color: C.series[4] },
    { from: "used", to: "dsp", value: nb.dsp_loss_t ?? 0, color: C.status.warning },
    { from: "used", to: "dead", value: nb.dead_soda_net_t ?? 0, color: C.status.serious },
    { from: "used", to: "phys", value: nb.physical_loss_t ?? 0, color: C.status.critical },
    { from: "used", to: "back", value: back, color: C.status.good },
  ];

  const totalLoss = (nb.dsp_loss_t ?? 0) + (nb.dead_soda_net_t ?? 0) + (nb.physical_loss_t ?? 0);

  return (
    <div className="space-y-3">
      <div className="rounded-xl p-3" style={{ background: C.surface, border: `1px solid ${C.grid}` }}>
        <p className="mb-2 text-sm font-semibold" style={{ color: C.ink }}>
          Sankey Natrium — ke mana uang NaOH mengalir (ton/jam)
        </p>
        <Sankey nodes={nodes} flows={flows} />
      </div>
      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
        <Stat label="Total kebocoran NaOH" val={`${totalLoss.toFixed(1)} t`} />
        <Stat label="• Kimiawi (DSP)" val={`${(nb.dsp_loss_t ?? 0).toFixed(1)} t · ${((nb.dsp_loss_t ?? 0) / mk * 100).toFixed(0)}%`} />
        <Stat label="• Soda mati (net)" val={`${(nb.dead_soda_net_t ?? 0).toFixed(1)} t`} />
        <Stat label="• Fisik (red mud)" val={`${(nb.physical_loss_t ?? 0).toFixed(1)} t`} />
      </div>
    </div>
  );
}
function Stat({ label, val }: { label: string; val: string }) {
  return (
    <div className="rounded-lg p-3" style={{ background: C.surface, border: `1px solid ${C.grid}` }}>
      <p className="text-xs" style={{ color: C.muted }}>{label}</p>
      <p className="text-lg font-bold" style={{ color: C.ink }}>{val}</p>
    </div>
  );
}
