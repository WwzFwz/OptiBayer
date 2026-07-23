"use client";
// Integrasi — kontrak antarmuka + playground (panggil API sungguhan).
import { useEffect, useState } from "react";
import { API, getContract, postOp } from "@/lib/api";
import { Spinner } from "@/components/ui/Feedback";
import { C } from "@/lib/theme";

type EP = { method: string; path: string; summary: string; consumer: string;
            example_payload: unknown };

export default function Integrasi() {
  const [spec, setSpec] = useState<{ endpoints: EP[]; mcp_tools: unknown[] } | null>(null);
  const [sel, setSel] = useState("predict");
  const [payload, setPayload] = useState("{}");
  const [res, setRes] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getContract().then((d) => setSpec(d as never)).catch(() => {});
  }, []);

  const ops = [
    ["predict", "POST /v1/predict"], ["mass-balance", "POST /v1/mass-balance"],
    ["optimize/pareto", "POST /v1/optimize/pareto"],
    ["optimize/goal-seek", "POST /v1/optimize/goal-seek"],
  ] as const;

  async function call() {
    setBusy(true);
    try {
      const p = JSON.parse(payload || "{}");
      setRes(await postOp(sel, p));
    } catch (e) { setRes({ error: String(e) }); }
    finally { setBusy(false); }
  }

  return (
    <div className="space-y-3">
      <div className="rounded-xl p-3" style={{ background: C.surface, border: `1px solid ${C.grid}` }}>
        <p className="mb-1 text-sm font-semibold" style={{ color: C.ink }}>
          Integrasi — kontrak antarmuka & playground
        </p>
        <p className="mb-3 text-xs" style={{ color: C.muted }}>
          Inti OptiBayer headless. REST API di <code>{API}</code> — dokumentasi
          OpenAPI: <code>{API}/docs</code>. Frontend ini & Streamlit sama-sama
          klien di atas kontrak yang sama.
        </p>
        {spec && (
          <div className="overflow-x-auto">
            <table className="w-full text-xs" style={{ color: C.ink2 }}>
              <thead><tr style={{ color: C.muted }}>
                <th className="p-1 text-left">Method</th><th className="p-1 text-left">Path</th>
                <th className="p-1 text-left">Fungsi</th><th className="p-1 text-left">Konsumen</th>
              </tr></thead>
              <tbody>
                {spec.endpoints.map((e, i) => {
                  // path /v1/optimize/pareto -> op "optimize/pareto"; /v1/predict -> "predict"
                  const op = e.path.replace(/^\/v1\//, "");
                  const playable = ops.some(([id]) => id === op);
                  return (
                    <tr key={i}
                        onClick={playable ? () => {
                          setSel(op);
                          setPayload(e.example_payload
                            ? JSON.stringify(e.example_payload, null, 2) : "{}");
                        } : undefined}
                        className={playable ? "cursor-pointer transition-colors hover:brightness-125" : ""}
                        title={playable ? "Klik untuk memuat ke Playground" : undefined}
                        style={{ borderTop: `1px solid ${C.grid}`,
                                 background: playable && sel === op ? C.accent + "18" : undefined }}>
                      <td className="p-1" style={{ color: C.accent }}>{e.method}</td>
                      <td className="p-1 font-mono">{e.path}</td>
                      <td className="p-1">{e.summary}</td>
                      <td className="p-1">{e.consumer}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="rounded-xl p-3" style={{ background: C.surface, border: `1px solid ${C.grid}` }}>
        <p className="mb-2 text-sm font-semibold" style={{ color: C.ink }}>Playground</p>
        <div className="flex flex-wrap gap-2">
          <select value={sel} onChange={(e) => setSel(e.target.value)}
                  className="rounded px-2 py-1.5 text-sm"
                  style={{ background: C.page, color: C.ink, border: `1px solid ${C.grid}` }}>
            {ops.map(([id, lbl]) => <option key={id} value={id}>{lbl}</option>)}
          </select>
          <button onClick={call} disabled={busy}
            className="btn-lift inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-semibold"
            style={{ background: C.accent, color: "#1a1408", opacity: busy ? 0.6 : 1 }}>
            {busy && <Spinner />}{busy ? "Memanggil…" : "Panggil"}
          </button>
        </div>
        <textarea value={payload} onChange={(e) => setPayload(e.target.value)}
                  rows={5} className="mt-2 w-full rounded p-2 font-mono text-xs"
                  style={{ background: C.page, color: C.ink, border: `1px solid ${C.grid}` }}
                  placeholder='{} = pakai contoh payload kontrak' />
        {res != null && (
          <pre className="mt-2 max-h-64 overflow-auto rounded p-2 text-xs"
               style={{ background: C.page, color: C.ink2, border: `1px solid ${C.grid}` }}>
            {JSON.stringify(res, null, 2)}
          </pre>
        )}
      </div>
    </div>
  );
}
