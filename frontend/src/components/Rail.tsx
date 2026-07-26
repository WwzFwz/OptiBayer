"use client";
// Rail navigasi ikon di kiri (pengganti tab atas Streamlit).
// Urutan mengikuti alur pabrik hulu→hilir; tooltip saat hover.
import {
  Activity, FlaskConical, Snowflake, Recycle, Beaker, BookOpen,
  Network, Share2, PanelLeft, Flame,
} from "lucide-react";
import { useStore } from "@/lib/store";
import { PageId } from "@/lib/pages";
import { C } from "@/lib/theme";

export type { PageId };

export const PAGES = [
  { id: "overview", label: "Overview", Icon: Activity },
  { id: "diagram", label: "Diagram Proses", Icon: Share2 },
  { id: "digesti", label: "Digesti", Icon: Flame },
  { id: "liquor", label: "Liquor Loop", Icon: FlaskConical },
  { id: "presipitasi", label: "Presipitasi", Icon: Snowflake },
  { id: "redmud", label: "Red Mud & CCUS", Icon: Recycle },
  { id: "lab", label: "Prediction Lab", Icon: Beaker },
  { id: "knowledge", label: "Knowledge", Icon: BookOpen },
  { id: "integrasi", label: "Integrasi", Icon: Network },
] as const;

export default function Rail({
  page, setPage,
}: { page: PageId; setPage: (p: PageId) => void }) {
  const { setPanelOpen } = useStore();
  return (
    <nav
      className="flex flex-col items-center gap-1 py-3 shrink-0"
      style={{ width: 60, background: C.surface, borderRight: `1px solid ${C.grid}` }}
    >
      <button
        onClick={() => setPanelOpen(true)}
        title="Panel Kendali"
        className="mb-2 grid place-items-center rounded-lg transition-colors"
        style={{ width: 40, height: 40, color: C.ink2 }}
      >
        <PanelLeft size={20} />
      </button>
      <div style={{ width: 28, height: 1, background: C.grid }} className="mb-1" />
      {PAGES.map(({ id, label, Icon }) => {
        const active = page === id;
        return (
          <button
            key={id}
            onClick={() => setPage(id)}
            title={label}
            className="group relative grid place-items-center rounded-lg transition-colors"
            style={{
              width: 40, height: 40,
              color: active ? C.ink : C.muted,
              background: active ? "#26262450" : "transparent",
            }}
          >
            {active && (
              <span
                className="absolute left-0 rounded-r"
                style={{ width: 3, height: 22, background: C.series[0] }}
              />
            )}
            <Icon size={20} />
            <span
              className="pointer-events-none absolute left-12 z-50 hidden whitespace-nowrap rounded px-2 py-1 text-xs group-hover:block"
              style={{ background: "#000", color: C.ink, border: `1px solid ${C.grid}` }}
            >
              {label}
            </span>
          </button>
        );
      })}
    </nav>
  );
}
