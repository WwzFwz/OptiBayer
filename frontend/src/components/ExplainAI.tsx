"use client";
// Analisis AI per chart — reusable. Grounded pada angka chart + knowledge
// ber-sitasi; tanpa LLM jatuh ke ringkasan template (di backend).
import { useState } from "react";
import { Sparkles } from "lucide-react";
import { explainChart } from "@/lib/api";
import { Spinner } from "@/components/ui/Feedback";
import { C } from "@/lib/theme";

export default function ExplainAI({ title, context, tags }: {
  title: string; context: unknown; tags?: string[];
}) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [ans, setAns] = useState<{ text: string; backend: string } | null>(null);
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    try { setAns(await explainChart(title, context, q, tags)); }
    catch (e) { setAns({ text: `Gagal: ${e}`, backend: "error" }); }
    finally { setBusy(false); }
  }

  return (
    <div className="mt-2 rounded-lg" style={{ border: `1px solid ${C.grid}` }}>
      <button onClick={() => setOpen(!open)} aria-expanded={open}
        className="flex w-full items-center gap-2 px-3 py-2 text-sm"
        style={{ color: C.accent }}>
        <Sparkles size={15} /> Analisis AI — {title}
        <span className="ml-auto text-xs" style={{ color: C.muted }}>{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div className="px-3 pb-3">
          <div className="flex gap-2">
            <input value={q} onChange={(e) => setQ(e.target.value)}
              placeholder="pertanyaan (opsional)…"
              className="flex-1 rounded px-2 py-1.5 text-sm"
              style={{ background: C.page, color: C.ink, border: `1px solid ${C.grid}` }} />
            <button onClick={run} disabled={busy}
              className="btn-lift inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-semibold"
              style={{ background: C.accent, color: "#1a1408", opacity: busy ? 0.6 : 1 }}>
              {busy && <Spinner />}{busy ? "Menganalisis…" : "Analisis"}
            </button>
          </div>
          {ans && (
            <div className="mt-2 text-sm" style={{ color: C.ink2 }}>
              <p className="whitespace-pre-wrap">{ans.text}</p>
              <p className="mt-1 text-xs" style={{ color: C.muted }}>
                backend: {ans.backend} · dihitung dari angka chart ini (grounded)
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
