"use client";
// Shell OptiBayer: rail ikon kiri + header + Panel Kendali overlay +
// panel Advisory yang bisa di-dock (atas / kanan, via drag atau toggle).
import { useState } from "react";
import { CircleAlert, Wifi, WifiOff } from "lucide-react";
import Advisory from "./Advisory";
import ControlPanel from "./ControlPanel";
import Kpi from "./Kpi";
import Rail, { PageId } from "./Rail";
import Overview from "./pages/Overview";
import Diagram from "./pages/Diagram";
import Digesti from "./pages/Digesti";
import Liquor from "./pages/Liquor";
import Presipitasi from "./pages/Presipitasi";
import RedMud from "./pages/RedMud";
import Lab from "./pages/Lab";
import Knowledge from "./pages/Knowledge";
import Integrasi from "./pages/Integrasi";
import { useStore } from "@/lib/store";
import { C } from "@/lib/theme";

const REPLAY_FREE: PageId[] = ["lab", "knowledge", "integrasi"];
// advisory PENUH hanya di Overview (pusat monitoring); halaman lain RINGKAS
// (Diagram sudah punya visual sendiri -> advisory penuh di sana = redundan).
const FULL_ADVISORY: PageId[] = ["overview"];

export default function Shell() {
  const s = useStore();
  const [page, setPage] = useState<PageId>("overview");
  const monitoring = !REPLAY_FREE.includes(page);
  const fullAdvisory = FULL_ADVISORY.includes(page);

  const day = Math.floor(s.hour / 24) + 1;
  const clock = s.hour % 24;
  const shift = Math.floor(clock / 8) + 1;
  const scenarioName = s.scenario === 1 ? "Gangguan: Silika Spike" : "Operasi Normal";

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: C.page }}>
      <Rail page={page} setPage={setPage} />
      <ControlPanel />

      <div className="flex min-w-0 flex-1 flex-col">
        {/* header */}
        <header className="flex items-center gap-3 px-4 py-3"
                style={{ borderBottom: `1px solid ${C.grid}` }}>
          <h1 className="text-lg font-bold" style={{ color: C.ink }}>
            OptiBayer <span className="font-normal" style={{ color: C.muted }}>· Konsol CRO</span>
          </h1>
          <span className="text-xs" style={{ color: C.muted }}>
            {monitoring
              ? `Hari ${day} · ${String(clock).padStart(2, "0")}:00 · Shift ${shift} · ${scenarioName}`
              : "Halaman bebas replay"}
          </span>
          <span className="ml-auto flex items-center gap-1 text-xs"
                style={{ color: s.apiDown ? C.status.critical : C.status.good }}>
            {s.apiDown ? <WifiOff size={14} /> : <Wifi size={14} />}
            {s.apiDown ? "API terputus" : "API tersambung"}
          </span>
        </header>

        {s.apiDown && (
          <div className="flex items-center gap-2 px-4 py-2 text-sm"
               style={{ background: "#d03b3b22", color: C.status.critical }}>
            <CircleAlert size={16} />
            Backend belum jalan — jalankan:&nbsp;
            <code style={{ color: C.ink2 }}>
              python -m uvicorn src.integration.api:app --port 8000
            </code>
          </div>
        )}

        {/* konten + dock kanan */}
        <div className="flex min-h-0 flex-1">
          <main className="min-w-0 flex-1 space-y-3 overflow-y-auto p-4">
            {monitoring && <Kpi />}
            {/* penuh (drag-dock top) hanya di overview & diagram; stasiun = ringkas */}
            {monitoring && fullAdvisory && s.dock === "top" && <Advisory setPage={setPage} />}
            {monitoring && !fullAdvisory && <Advisory setPage={setPage} compact />}
            {page === "overview" && <Overview />}
            {page === "diagram" && <Diagram />}
            {page === "digesti" && <Digesti />}
            {page === "liquor" && <Liquor />}
            {page === "presipitasi" && <Presipitasi />}
            {page === "redmud" && <RedMud />}
            {page === "lab" && <Lab />}
            {page === "knowledge" && <Knowledge />}
            {page === "integrasi" && <Integrasi />}
          </main>
          {monitoring && fullAdvisory && s.dock === "right" && (
            <aside className="w-[340px] shrink-0 overflow-y-auto p-3"
                   style={{ borderLeft: `1px solid ${C.grid}` }}>
              <Advisory setPage={setPage} />
            </aside>
          )}
        </div>
      </div>
    </div>
  );
}

