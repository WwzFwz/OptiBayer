"use client";
// Panel Advisory — bisa DIPINDAH user: seret handle ke tepi kanan layar
// untuk dock kanan, seret ke atas untuk kembali ke atas. (drag pointer
// murni; tombol di dalam kartu tetap berfungsi karena drag hanya di handle)
import { useRef, useState } from "react";
import { Check, GripHorizontal, Map, X } from "lucide-react";
import { Card } from "@/lib/api";
import { useStore } from "@/lib/store";
import { useToast } from "./ui/Toast";
import { C, Severity } from "@/lib/theme";
import { PageId } from "./Rail";

const SEV_LABEL: Record<Severity, string> = {
  critical: "CRITICAL", serious: "SERIOUS", warning: "WARNING",
  info: "INFO", good: "OK",
};

const PER_PAGE = 3;

export default function Advisory({ setPage }: { setPage: (p: PageId) => void }) {
  const s = useStore();
  const [dragging, setDragging] = useState(false);
  const [ghost, setGhost] = useState<{ x: number; y: number } | null>(null);
  const [pageIdx, setPageIdx] = useState(0);
  const startPos = useRef<{ x: number; y: number } | null>(null);

  const cards = s.hourData?.cards ?? [];
  const right = s.dock === "right";
  // pagination: dock kanan (sempit) => 3/hal; dock atas (lebar) => 6/hal
  const perPage = right ? PER_PAGE : PER_PAGE * 2;
  const nPages = Math.max(1, Math.ceil(cards.length / perPage));
  const pi = Math.min(pageIdx, nPages - 1);
  const shown = cards.slice(pi * perPage, pi * perPage + perPage);

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
             style={{ width: 320, background: C.accent + "22",
                      borderLeft: `2px dashed ${C.accent}` }} />
      )}
      {dragging && ghost && (
        <div className="pointer-events-none fixed z-50 rounded px-3 py-2 text-xs"
             style={{ left: ghost.x + 12, top: ghost.y + 12,
                      background: C.surface, border: `1px solid ${C.accent}`,
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
          <span className="ml-auto text-[0.65rem]" style={{ color: C.muted }}>
            {right ? "dock kanan" : "dock atas"} · seret ⠿
          </span>
        </header>
        <div className={right
          ? "flex flex-col gap-2 p-2"
          : "grid gap-2 p-2 md:grid-cols-2 xl:grid-cols-3"}>
          {cards.length === 0 && (
            <p className="p-3 text-sm" style={{ color: C.muted }}>
              {s.loadingHour ? "Memuat advisory…" : "Tidak ada advisory jam ini."}
            </p>
          )}
          {shown.map((c, i) => (
            <AdvisoryCard key={`${s.hour}-${pi}-${i}`} card={c}
                          decisionKey={`${s.scenario}-${s.hour}-${c.title}`}
                          setPage={setPage} />
          ))}
        </div>
        {/* pagination */}
        {nPages > 1 && (
          <div className="flex items-center justify-center gap-2 border-t px-3 py-2"
               style={{ borderColor: C.grid }}>
            <button onClick={() => setPageIdx(Math.max(0, pi - 1))}
              disabled={pi === 0}
              className="rounded-lg px-2 py-1 text-xs disabled:opacity-40"
              style={{ border: `1px solid ${C.grid}`, color: C.ink2 }}>‹ Sebelumnya</button>
            <div className="flex gap-1">
              {Array.from({ length: nPages }, (_, k) => (
                <button key={k} onClick={() => setPageIdx(k)}
                  className="h-2 w-2 rounded-full"
                  style={{ background: k === pi ? C.accent : C.grid }}
                  aria-label={`halaman ${k + 1} dari ${nPages}`}
                  aria-current={k === pi ? "page" : undefined} />
              ))}
            </div>
            <button onClick={() => setPageIdx(Math.min(nPages - 1, pi + 1))}
              disabled={pi === nPages - 1}
              className="rounded-lg px-2 py-1 text-xs disabled:opacity-40"
              style={{ border: `1px solid ${C.grid}`, color: C.ink2 }}>Berikutnya ›</button>
            <span className="ml-1 text-[0.65rem]" style={{ color: C.muted }}>
              {pi + 1}/{nPages}
            </span>
          </div>
        )}
      </section>
    </>
  );
}

function AdvisoryCard({ card, decisionKey, setPage }: {
  card: Card; decisionKey: string; setPage: (p: PageId) => void;
}) {
  const s = useStore();
  const toast = useToast();
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
        <div className="grid grid-cols-3 gap-2">
          <Btn bg={C.status.good} label={`Terima: ${card.title}`}
               onClick={() => {
                 s.decide(decisionKey, "terima", card.title);
                 toast("success", `Advisory diterima — ${card.title}`);
               }}>
            <Check size={13} /> Terima
          </Btn>
          <Btn outline={C.status.critical} label={`Tolak: ${card.title}`}
               onClick={() => {
                 s.decide(decisionKey, "tolak", card.title);
                 toast("info", `Advisory ditolak — tercatat di audit`);
               }}>
            <X size={13} /> Tolak
          </Btn>
          <Btn outline={C.grid} label="Buka peta operasi"
               onClick={() => setPage("digesti")}>
            <Map size={13} /> Peta
          </Btn>
        </div>
      ))}
    </article>
  );
}

function Btn({ children, bg, outline, onClick, label }: {
  children: React.ReactNode; bg?: string; outline?: string;
  onClick: () => void; label?: string;
}) {
  return (
    <button onClick={onClick} aria-label={label}
      className={`flex w-full items-center justify-center gap-1.5 rounded-lg px-3 py-2 text-xs font-semibold${bg ? " btn-lift" : ""}`}
      style={bg
        ? { background: bg, color: "#fff" }
        : { border: `1px solid ${outline}`, color: outline === C.grid ? C.ink2 : outline }}>
      {children}
    </button>
  );
}
