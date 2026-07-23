"use client";
// Panel Kendali sebagai OVERLAY kiri (dibuka tombol ☰ di rail) — menimpa
// konten, bukan mendorong. Isi: skenario, replay, kecepatan, dock advisory.
import { X, Play, Pause, SkipForward } from "lucide-react";
import { useStore } from "@/lib/store";
import { C } from "@/lib/theme";

export default function ControlPanel() {
  const s = useStore();
  if (!s.panelOpen) return null;
  return (
    <>
      <div
        className="fixed inset-0 z-40"
        style={{ background: "rgba(0,0,0,0.5)" }}
        onClick={() => s.setPanelOpen(false)}
      />
      <aside
        className="fixed left-0 top-0 z-50 h-full overflow-y-auto p-4"
        style={{ width: 300, background: C.surface, borderRight: `1px solid ${C.grid}`, color: C.ink }}
      >
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-bold">Panel Kendali</h2>
          <button onClick={() => s.setPanelOpen(false)} style={{ color: C.muted }}>
            <X size={20} />
          </button>
        </div>

        <Label>Skenario Demo</Label>
        <select
          value={s.scenario}
          onChange={(e) => s.setScenario(Number(e.target.value))}
          className="mb-4 w-full rounded px-2 py-2 text-sm"
          style={{ background: C.page, color: C.ink, border: `1px solid ${C.grid}` }}
        >
          <option value={0}>Operasi Normal</option>
          <option value={1}>Gangguan: Silika Spike</option>
        </select>

        <div className="mb-4 flex gap-2">
          <button
            onClick={() => s.setPlaying(!s.playing)}
            aria-pressed={s.playing}
            aria-label={s.playing ? "Jeda replay" : "Mainkan replay"}
            className="btn-lift flex flex-1 items-center justify-center gap-1 rounded-lg py-2 text-sm font-semibold"
            style={{ background: s.playing ? C.status.warning : C.status.good, color: "#fff" }}
          >
            {s.playing ? <Pause size={16} /> : <Play size={16} />}
            {s.playing ? "Pause" : "Play"}
          </button>
          <button
            onClick={() => s.seq && s.setHour(Math.min(s.hour + 1, s.seq.n - 1))}
            aria-label="Maju satu jam"
            className="flex items-center justify-center rounded-lg px-3"
            style={{ border: `1px solid ${C.grid}`, color: C.ink2 }}
          >
            <SkipForward size={16} />
          </button>
        </div>

        <Label>Jam simulasi: {s.hour}</Label>
        <input
          type="range" min={0} max={(s.seq?.n ?? 96) - 1} value={s.hour}
          onChange={(e) => s.setHour(Number(e.target.value))}
          className="mb-4 w-full"
        />

        <Label>Kecepatan: {(s.speedMs / 1000).toFixed(1)} dtk/jam</Label>
        <input
          type="range" min={500} max={5000} step={500} value={s.speedMs}
          onChange={(e) => s.setSpeedMs(Number(e.target.value))}
          className="mb-4 w-full"
        />

        <div style={{ height: 1, background: C.grid }} className="my-4" />

        <Label>Tata letak Advisory</Label>
        <div className="flex gap-2">
          {(["top", "right"] as const).map((d) => (
            <button
              key={d}
              onClick={() => s.setDock(d)}
              aria-pressed={s.dock === d}
              className="flex-1 rounded-lg py-2 text-sm capitalize"
              style={{
                border: `1px solid ${s.dock === d ? C.accent : C.grid}`,
                background: s.dock === d ? "#26262450" : "transparent",
                color: s.dock === d ? C.ink : C.muted,
              }}
            >
              {d === "top" ? "Atas" : "Panel Kanan"}
            </button>
          ))}
        </div>
        <p className="mt-2 text-xs" style={{ color: C.muted }}>
          Atau seret panel advisory ke tepi kanan untuk memindahkannya.
        </p>
      </aside>
    </>
  );
}

function Label({ children }: { children: React.ReactNode }) {
  return (
    <p className="mb-1 text-xs font-semibold uppercase tracking-wide"
       style={{ color: C.muted }}>{children}</p>
  );
}
