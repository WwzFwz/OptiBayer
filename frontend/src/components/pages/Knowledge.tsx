"use client";
// Knowledge — daftar + search + chips "dipakai oleh" + TAMBAH dokumen
// (tulis langsung: nama, tag chart, isi) → langsung dipakai AI tanpa restart.
import { useEffect, useState } from "react";
import { addKnowledge, getKnowledge, KnowledgeDoc } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import { Spinner } from "@/components/ui/Feedback";
import { C } from "@/lib/theme";

export default function Knowledge() {
  const [docs, setDocs] = useState<KnowledgeDoc[]>([]);
  const [charts, setCharts] = useState<Record<string, string>>({});
  const [q, setQ] = useState("");
  const [open, setOpen] = useState<string | null>(null);

  // form tambah
  const [name, setName] = useState("");
  const [body, setBody] = useState("");
  const [picked, setPicked] = useState<string[]>([]);
  const [extra, setExtra] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const toast = useToast();

  function reload() {
    getKnowledge().then((d) => { setDocs(d.docs); setCharts(d.charts); }).catch(() => {});
  }
  useEffect(reload, []);

  const shown = q.trim()
    ? docs.filter((d) => (d.name + d.tags.join() + d.body).toLowerCase().includes(q.toLowerCase()))
    : docs;

  async function save() {
    if (!name.trim() || !body.trim()) {
      setMsg("Nama & isi wajib diisi."); toast("error", "Nama & isi wajib diisi.");
      return;
    }
    setBusy(true); setMsg(null);
    try {
      const r = await addKnowledge({
        name, body, charts: picked,
        extra_tags: extra.split(",").map((s) => s.trim()).filter(Boolean),
      });
      setMsg(`Tersimpan: ${r.saved} — langsung dipakai AI.`);
      toast("success", `Dokumen "${r.saved}" tersimpan — langsung dipakai AI.`);
      setName(""); setBody(""); setPicked([]); setExtra("");
      reload();
    } catch (e) { setMsg(`Gagal: ${e}`); toast("error", `Gagal menyimpan: ${e}`); }
    finally { setBusy(false); }
  }

  return (
    <div className="grid gap-3 lg:grid-cols-5">
      {/* daftar (kiri) */}
      <div className="lg:col-span-3 rounded-xl p-3" style={{ background: C.surface, border: `1px solid ${C.grid}` }}>
        <p className="mb-1 text-sm font-semibold" style={{ color: C.ink }}>
          Knowledge Pabrik — sumber pengetahuan AI
        </p>
        <p className="mb-3 text-xs" style={{ color: C.muted }}>
          Dokumen ber-tag otomatis menjadi konteks AI (AI wajib mengutip nama
          dokumen). Tiga sumber kecerdasan: data (ML) + fisika + expert (ini).
        </p>
        <input value={q} onChange={(e) => setQ(e.target.value)}
               placeholder="cari judul / tag / isi…"
               className="mb-3 w-full rounded px-3 py-2 text-sm"
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
                       style={{ background: "#fab21922", color: C.status.warning }}>{d.status}</p>
                  )}
                  {d.used_by.length > 0 ? (
                    <p className="mb-2 text-xs" style={{ color: C.ink2 }}>
                      <b>Dipakai oleh:</b> {d.used_by.join(" · ")}
                    </p>
                  ) : (
                    <p className="mb-2 text-xs" style={{ color: C.status.warning }}>
                      Belum cocok chart mana pun — tambahkan tag yang dikenali.
                    </p>
                  )}
                  <pre className="whitespace-pre-wrap text-xs" style={{ color: C.ink2 }}>{d.body}</pre>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* tambah (kanan) */}
      <div className="lg:col-span-2 rounded-xl p-3" style={{ background: C.surface, border: `1px solid ${C.grid}` }}>
        <p className="mb-2 text-sm font-semibold" style={{ color: C.ink }}>
          Tambah dokumen (expert ANTAM)
        </p>
        <input value={name} onChange={(e) => setName(e.target.value)}
               placeholder="nama, mis. sop-mud-washing"
               className="mb-2 w-full rounded px-2 py-1.5 text-sm"
               style={{ background: C.page, color: C.ink, border: `1px solid ${C.grid}` }} />

        <p className="mb-1 text-xs" style={{ color: C.muted }}>Rekomendasikan untuk chart:</p>
        <div className="mb-2 flex flex-wrap gap-1">
          {Object.entries(charts).map(([id, label]) => {
            const on = picked.includes(id);
            return (
              <button key={id} aria-pressed={on}
                onClick={() => setPicked(on ? picked.filter((x) => x !== id) : [...picked, id])}
                className="rounded-full px-2 py-1 text-xs"
                style={{ border: `1px solid ${on ? C.accent : C.grid}`,
                         background: on ? C.accent + "22" : "transparent",
                         color: on ? C.ink : C.muted }}>
                {label}
              </button>
            );
          })}
        </div>

        <input value={extra} onChange={(e) => setExtra(e.target.value)}
               placeholder="tag tambahan (pisah koma)"
               className="mb-2 w-full rounded px-2 py-1.5 text-sm"
               style={{ background: C.page, color: C.ink, border: `1px solid ${C.grid}` }} />
        <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={6}
                  placeholder="Tulis SOP / catatan pakar (markdown)…"
                  className="mb-2 w-full rounded p-2 text-sm"
                  style={{ background: C.page, color: C.ink, border: `1px solid ${C.grid}` }} />
        <p className="mb-2 text-xs" style={{ color: C.muted }}>
          Pemetaan ini rekomendasi lentur — dokumen dipakai chart mana pun yang
          tag-nya beririsan; ubah tag = ubah pemakainya.
        </p>
        <button onClick={save} disabled={busy}
          className="btn-lift flex w-full items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold"
          style={{ background: C.status.good, color: "#fff", opacity: busy ? 0.6 : 1 }}>
          {busy && <Spinner />}{busy ? "Menyimpan…" : "Simpan dokumen"}
        </button>
        {msg && <p className="mt-2 text-xs" style={{ color: msg.startsWith("Gagal") ? C.status.critical : C.status.good }}>{msg}</p>}
      </div>
    </div>
  );
}
