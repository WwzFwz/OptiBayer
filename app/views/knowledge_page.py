"""Halaman Knowledge — pengetahuan expert pabrik yang dipakai AI sebagai konteks.

Tier-1 Knowledge Pack (tanpa vector DB, lihat src/advisory/knowledge.py).
Konten saat ini MOCK; arsitektur siap menerima dokumen expert ANTAM asli.
"""

from __future__ import annotations

import re

import streamlit as st

from app import ui
from src.advisory import knowledge


def render() -> None:
    st.subheader("Knowledge Pabrik — sumber pengetahuan AI")
    st.caption(
        "Dokumen di folder `knowledge/` otomatis menjadi konteks tombol "
        "'Analisis AI' (dicocokkan via tag; AI wajib mengutip nama dokumen). "
        "Tiga sumber kecerdasan sistem: data historian (ML) + hukum fisika "
        "(neraca massa) + **pengalaman expert (halaman ini)**. "
        "Produksi: kurasi hanya oleh expert + versioning (doc 07); dokumen "
        "ratusan → upgrade ke vector store."
    )

    docs = knowledge.load_all()
    left, right = st.columns([3, 2])

    with left:
        st.markdown(f"**{len(docs)} dokumen aktif**")
        for d in docs:
            label = f"{d['name']}  ·  tag: {', '.join(d['tags']) or '—'}"
            with st.expander(label):
                if d["status"]:
                    st.warning(d["status"], icon=":material/pending_actions:")
                st.markdown(d["body"])

    with right:
        with st.container(border=True):
            st.markdown("**Tambah dokumen** (expert ANTAM)")
            up = st.file_uploader(
                "Upload .md / .txt", type=["md", "txt"], key="kn_upload",
                help="Baris pertama file: `tags: a, b, c` supaya AI tahu "
                     "kapan memakainya",
            )
            if up is not None:
                safe = re.sub(r"[^A-Za-z0-9._-]", "_", up.name)
                if not safe.endswith(".md"):
                    safe += ".md"
                dest = knowledge.KNOWLEDGE_DIR / safe
                if st.button("Simpan ke Knowledge Pack", type="primary",
                             icon=":material/save:", key="kn_save"):
                    knowledge.KNOWLEDGE_DIR.mkdir(exist_ok=True)
                    dest.write_bytes(up.getvalue())
                    st.success(f"Tersimpan: `{safe}` — langsung dipakai AI "
                               "(tanpa restart).")
        st.caption(
            "Format: baris 1 `tags: ...`, baris 2 opsional `status: ...`, "
            "sisanya markdown bebas. Aturan kuantitatif dari expert juga bisa "
            "diangkat jadi guardrail deterministik (roadmap)."
        )
