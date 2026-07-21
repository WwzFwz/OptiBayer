"use client";
// Panel Advisory — bisa DIPINDAH user: seret handle ke tepi kanan layar
// untuk dock kanan, seret ke atas untuk kembali ke atas. (drag pointer
// murni; tombol di dalam kartu tetap berfungsi karena drag hanya di handle)
import { useRef, useState } from "react";
import { Check, GripHorizontal, Map, X } from "lucide-react";
import { Card } from "@/lib/api";
import { useStore } from "@/lib/store";
import { C, Severity } from "@/lib/theme";
import { PageId } from "./Rail";

const SEV_LABEL: Record<Severity, string> = {
  critical: "CRITICAL", serious: "SERIOUS", warning: "WARNING",
  info: "INFO", good: "OK",
};

export default function Advisory({ setPage }: { setPage: (p: PageId) => void }) {
  const s = useStore();
  const [dragging, setDragging] = useState(false);
  const [ghost, setGhost] = useState<{ x: number; y: number } | null>(null);
  const startPos = useRef<{ x: number; y: number } | null>(null);

  const cards = s.hourData?.cards ?? [];

  function onPointerDown(e: React.PointerEvent) {
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    startPos.current = { x: e.clientX, y: e.clientY };
  }
  function onPointerMove(e: React.PointerEvent) {
    if (!startPos.current) return;
    const dx = e.clientX - startPos.current.x;
    const dy = e.clientY - startPos.current.y;
    if (!dragging && Math.hypot(dx, dy) > 8) setDragging(true);
    if (dragging || Math.hypot(dx, dy) > 8) setGhost({ x: e.clientX, y: e.clientY });
  }
  function onPointerUp(e: React.PointerEvent) {
    if (dragging) {
      const nearRight = e.clientX > window.innerWidth - 320;
      s.setDock(nearRight ? "right" : "top");
    }
    setDragging(false); setGhost(null); startPos.current = null;
  }

  return (
    <>
      {/* drop-zone highlight saat drag */}
      {dragging && (
        <div className="pointer-events-none fixed inset-y-0 right-0 z-40"
             style={{ width: 320, background: "#3987e522",
                      borderLeft: `2px dashed ${C.series[0]}` }} />
      )}
      {dragging && ghost && (
        <div className="pointer-events-none fixed z-50 rounded px-3 py-2 text-xs"
             style={{ left: ghost.x + 12, top: ghost.y + 12,
                      background: C.surface, border: `1px solid ${C.series[0]}`,
                      color: C.ink }}>
          Lepas di tepi kanan → panel kanan · di tengah → atas
        </div>
      )}

      <section
        className="rounded-xl"
        style={{ background: C.surface, border: `1px solid ${C.grid}` }}
      >
        <header
          className="flex cursor-grab select-none items-center gap-2 px-3 py-2"
          style={{ borderBottom: `1px solid ${C.grid}`, touchAction: "none" }}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          title="Seret untuk memindahkan panel"
        >
          <GripHorizontal size={16} style={{ color: C.muted }} />
          <span className="text-sm font-bold" style={{ color: C.ink }}>Advisory</span>
          <span className="text-xs" style={{ color: C.muted }}>
            {cards.length} kartu · {s.hourData?.fast ? "mode Play (ringkas)" : "analisis penuh"}
          </span>
        </header>
        <div className={s.dock === "right"
          ? "flex flex-col gap-2 p-2"
          : "grid gap-2 p-2 md:grid-cols-2 xl:grid-cols-3"}>
          {cards.length === 0 && (
            <p className="p-3 text-sm" style={{ color: C.muted }}>
              {s.loadingHour ? "Memuat advisory…" : "Tidak ada advisory jam ini."}
            </p>
          )}
          {cards.map((c, i) => (
            <AdvisoryCard key={`${s.hour}-${i}`} card={c}
                          decisionKey={`${s.scenario}-${s.hour}-${c.title}`}
                          setPage={setPage} />
          ))}
        </div>
      </section>
    </>
  );
}

function AdvisoryCard({ card, decisionKey, setPage }: {
  card: Card; decisionKey: string; setPage: (p: PageId) => void;
}) {
  const s = useStore();
  const sev = C.status[card.severity as Severity] ?? C.status.info;
  const decided = s.decisions[decisionKey];
  return (
    <article className="rounded-lg p-3"
             style={{ background: C.page, borderLeft: `3px solid ${sev}` }}>
      <p className="text-xs font-bold" style={{ color: sev }}>
        {SEV_LABEL[card.severity as Severity] ?? card.severity}
      </p>
      <h3 className="mb-1 text-sm font-semibold" style={{ color: C.ink }}>
        {card.title}
      </h3>
      <p className="text-xs" style={{ color: C.ink2 }}>
        <b>Dampak:</b> {card.impact}
      </p>
      <p className="text-xs" style={{ color: C.ink2 }}>
        <b>Tindakan:</b> {card.action}
      </p>
      <p className="mb-2 text-xs" style={{ color: C.muted }}>
        {card.why} · confidence: {card.confidence}
      </p>
      {card.severity !== "info" && (decided ? (
        <p className="text-xs font-bold"
           style={{ color: decided === "terima" ? C.status.good : C.status.critical }}>
          {decided === "terima" ? "✓ DITERIMA" : "✗ DITOLAK"} — tercatat
        </p>
      ) : (
        <div className="flex gap-1">
          <Btn bg={C.status.good} onClick={() => s.decide(decisionKey, "terima")}>
            <Check size={12} /> Terima
          </Btn>
          <Btn outline={C.status.critical}
               onClick={() => s.decide(decisionKey, "tolak")}>
            <X size={12} /> Tolak
          </Btn>
          <Btn outline={C.grid} onClick={() => setPage("digesti")}>
            <Map size={12} /> Peta
          </Btn>
        </div>
      ))}
    </article>
  );
}

function Btn({ children, bg, outline, onClick }: {
  children: React.ReactNode; bg?: string; outline?: string; onClick: () => void;
}) {
  return (
    <button onClick={onClick}
      className="flex items-center gap-1 rounded px-2 py-1 text-xs font-semibold transition-opacity hover:opacity-80"
      style={bg
        ? { background: bg, color: "#fff" }
        : { border: `1px solid ${outline}`, color: outline === C.grid ? C.ink2 : outline }}>
      {children}
    </button>
  );
}
