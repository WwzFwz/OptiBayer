"use client";
// Knowledge — daftar dokumen expert + chart pemakainya + pencarian.
import { useEffect, useState } from "react";
import { getKnowledge, KnowledgeDoc } from "@/lib/api";
import { C } from "@/lib/theme";

export default function Knowledge() {
  const [docs, setDocs] = useState<KnowledgeDoc[]>([]);
  const [q, setQ] = useState("");
  const [open, setOpen] = useState<string | null>(null);

  useEffect(() => {
    getKnowledge().then((d) => setDocs(d.docs)).catch(() => {});
  }, []);

  const shown = q.trim()
    ? docs.filter((d) => (d.name + d.tags.join() + d.body).toLowerCase().includes(q.toLowerCase()))
    : docs;

  return (
    <div className="space-y-3">
      <div className="rounded-xl p-3" style={{ background: C.surface, border: `1px solid ${C.grid}` }}>
        <p className="mb-1 text-sm font-semibold" style={{ color: C.ink }}>
          Knowledge Pabrik — sumber pengetahuan AI
        </p>
        <p className="mb-3 text-xs" style={{ color: C.muted }}>
          Dokumen ber-tag otomatis menjadi konteks AI (dicocokkan via tag; AI
          wajib mengutip nama dokumen). Tiga sumber kecerdasan: data (ML) +
          fisika (neraca massa) + pengalaman expert (halaman ini).
        </p>
        <input value={q} onChange={(e) => setQ(e.target.value)}
               placeholder="cari judul / tag / isi…"
               className="mb-3 w-full max-w-md rounded px-3 py-2 text-sm"
               style={{ background: C.page, color: C.ink, border: `1px solid ${C.grid}` }} />
        <p className="mb-2 text-xs" style={{ color: C.muted }}>
          {shown.length} dari {docs.length} dokumen
        </p>
        <div className="space-y-2">
          {shown.map((d) => (
            <div key={d.name} className="rounded-lg" style={{ background: C.page, border: `1px solid ${C.grid}` }}>
              <button onClick={() => setOpen(open === d.name ? null : d.name)}
                className="flex w-full items-center justify-between p-3 text-left">
                <span className="text-sm font-semibold" style={{ color: C.ink }}>{d.name}</span>
                <span className="text-xs" style={{ color: C.muted }}>tag: {d.tags.join(", ") || "—"}</span>
              </button>
              {open === d.name && (
                <div className="border-t p-3" style={{ borderColor: C.grid }}>
                  {d.status && (
                    <p className="mb-2 rounded px-2 py-1 text-xs"
                       style={{ background: "#fab21922", color: C.status.warning }}>
                      {d.status}
                    </p>
                  )}
                  {d.used_by.length > 0 && (
                    <p className="mb-2 text-xs" style={{ color: C.ink2 }}>
                      <b>Dipakai oleh:</b> {d.used_by.map((c) => `\`${c}\``).join(" · ")}
                    </p>
                  )}
                  <pre className="whitespace-pre-wrap text-xs" style={{ color: C.ink2 }}>{d.body}</pre>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
