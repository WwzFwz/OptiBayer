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
        q = st.text_input(
            "Cari dokumen", key="kn_search", placeholder="cari judul / tag / isi…",
            icon=":material/search:",
        )
        shown = docs
        if q.strip():
            needle = q.strip().lower()
            shown = [d for d in docs
                     if needle in d["name"].lower()
                     or needle in " ".join(d["tags"]).lower()
                     or needle in d["body"].lower()]
        st.markdown(f"**{len(shown)} dari {len(docs)} dokumen**"
                    + (f" · filter: `{q.strip()}`" if q.strip() else ""))
        if not shown:
            st.caption("Tidak ada dokumen cocok — coba kata kunci lain.")
        for d in shown:
            label = f"{d['name']}  ·  tag: {', '.join(d['tags']) or '—'}"
            with st.expander(label):
                if d["status"]:
                    st.warning(d["status"], icon=":material/pending_actions:")
                used_by = knowledge.charts_for_doc(d)
                if used_by:
                    st.markdown(
                        "**Dipakai oleh:** "
                        + " · ".join(f"`{c}`" for c in used_by)
                    )
                else:
                    st.info(
                        "Tag dokumen ini belum beririsan dengan chart mana pun "
                        "— tambahkan tag yang dikenali (lihat form) agar "
                        "dipakai tombol Analisis AI.", icon=":material/label_off:",
                    )
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
        with st.container(border=True):
            st.markdown("**Atau tulis langsung**")
            t_name = st.text_input("Nama dokumen", key="kn_name",
                                   placeholder="mis. sop-mud-washing")
            chart_labels = {spec["label"]: key
                            for key, spec in knowledge.CHART_TAGS.items()}
            t_charts = st.multiselect(
                "Rekomendasikan untuk chart", list(chart_labels), key="kn_charts",
                placeholder="pilih satu / beberapa chart…",
                help="Tag chart terpilih ditambahkan otomatis ke dokumen.",
            )
            t_tags = st.text_input(
                "Tag tambahan (opsional, pisah koma)", key="kn_tags",
                placeholder="mis. washing, blending",
            )
            st.caption(
                ":material/info: Pemetaan ini **rekomendasi lentur**, bukan "
                "ikatan tetap — dokumen dipakai oleh chart mana pun yang "
                "tag-nya beririsan. Mengubah tag di kemudian hari otomatis "
                "mengubah chart pemakainya."
            )
            t_body = st.text_area("Isi (markdown)", key="kn_body", height=160,
                                  placeholder="Tulis SOP / catatan pakar di sini…")
            if st.button("Simpan dokumen", type="primary",
                         icon=":material/save:", key="kn_save_direct"):
                if not t_name.strip() or not t_body.strip():
                    st.error("Nama & isi wajib diisi.")
                else:
                    tag_set: list[str] = []
                    for lbl in t_charts:
                        for tg in knowledge.CHART_TAGS[chart_labels[lbl]]["tags"]:
                            if tg not in tag_set:
                                tag_set.append(tg)
                    for tg in (t.strip() for t in t_tags.split(",")):
                        if tg and tg not in tag_set:
                            tag_set.append(tg)
                    safe = re.sub(r"[^A-Za-z0-9._-]", "-", t_name.strip().lower())
                    dest = knowledge.KNOWLEDGE_DIR / f"{safe}.md"
                    knowledge.KNOWLEDGE_DIR.mkdir(exist_ok=True)
                    dest.write_text(
                        f"tags: {', '.join(tag_set)}\n"
                        f"status: ditulis via dashboard — menunggu review\n\n"
                        f"{t_body.strip()}\n",
                        encoding="utf-8",
                    )
                    st.success(f"Tersimpan: `{safe}.md` — langsung dipakai AI.")

        st.caption(
            "Format: baris 1 `tags: ...`, baris 2 opsional `status: ...`, "
            "sisanya markdown bebas. Aturan kuantitatif dari expert juga bisa "
            "diangkat jadi guardrail deterministik (roadmap); produksi: kurasi "
            "berperan + approval (doc 07/08)."
        )
