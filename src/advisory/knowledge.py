"""Knowledge Pack (tier-1, tanpa vector DB) — pengetahuan expert sebagai konteks AI.

Arsitektur: folder `knowledge/` berisi markdown pendek per topik. Baris pertama
tiap file: `tags: a, b, c` (dipakai pencocokan sederhana), baris kedua opsional
`status: ...`. Konsumen (`providers.explain_chart`, advisory) meminta dokumen
via tag; AI diwajibkan MENGUTIP nama dokumen sumber.

Kenapa bukan RAG/embeddings: volume knowledge operasional pabrik (SOP, batas
operasi, catatan pakar) puluhan halaman — pencocokan tag cukup, nol dependensi,
mudah diaudit. Jalur upgrade ke vector store (FAISS/Chroma) terdokumentasi di
docs/07 bila dokumen tumbuh ke ratusan (manual vendor, laporan lab bertahun).

Konten saat ini MOCK (lihat `status:` tiap file) — arsitektur siap, isi tinggal
divalidasi/diganti expert ANTAM.
"""

from __future__ import annotations

from pathlib import Path

KNOWLEDGE_DIR = Path(__file__).resolve().parents[2] / "knowledge"
MAX_DOCS_PER_QUERY = 3
MAX_CHARS_PER_DOC = 2200


def load_all() -> list[dict]:
    """Semua dokumen: [{name, tags, status, body}] — dibaca segar tiap panggilan
    (file kecil; dokumen yang baru di-upload langsung terpakai tanpa restart)."""
    docs = []
    if not KNOWLEDGE_DIR.exists():
        return docs
    for p in sorted(KNOWLEDGE_DIR.glob("*.md")):
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        lines = text.splitlines()
        tags: list[str] = []
        status = ""
        body_start = 0
        for i, line in enumerate(lines[:4]):
            low = line.strip().lower()
            if low.startswith("tags:"):
                tags = [t.strip() for t in line.split(":", 1)[1].split(",") if t.strip()]
                body_start = i + 1
            elif low.startswith("status:"):
                status = line.split(":", 1)[1].strip()
                body_start = i + 1
        body = "\n".join(lines[body_start:]).strip()
        docs.append({"name": p.name, "tags": tags, "status": status, "body": body})
    return docs


def for_tags(tags: list[str] | None) -> list[dict]:
    """Dokumen yang tag-nya beririsan dengan `tags`, terbatas MAX_DOCS_PER_QUERY."""
    if not tags:
        return []
    want = {t.strip().lower() for t in tags}
    hits = [d for d in load_all() if want & {t.lower() for t in d["tags"]}]
    return hits[:MAX_DOCS_PER_QUERY]


def as_prompt_block(tags: list[str] | None) -> str:
    """Blok teks knowledge utk disisipkan ke prompt LLM (kosong bila tak ada)."""
    docs = for_tags(tags)
    if not docs:
        return ""
    parts = ["\n\nKNOWLEDGE PABRIK (kutip nama dokumen bila dipakai):"]
    for d in docs:
        status = f" [{d['status']}]" if d["status"] else ""
        parts.append(f"--- {d['name']}{status} ---\n{d['body'][:MAX_CHARS_PER_DOC]}")
    return "\n".join(parts)
