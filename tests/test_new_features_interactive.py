"""Uji interaktif tambahan (bukan bagian test suite asli) — khusus menekan
tombol & mengubah slider di fitur BARU (Prediction Lab, Overview) untuk
memastikan tidak ada exception tersembunyi yang lolos dari smoke test dasar.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest


def check(at, label):
    if at.exception:
        print(f"❌ GAGAL setelah {label}:")
        for e in at.exception:
            print(e)
        sys.exit(1)
    print(f"✅ OK setelah {label}  (metric={len(at.metric)}, warning={len(at.warning)}, error={len(at.error)})")


def main():
    at = AppTest.from_file(str(ROOT / "app" / "main.py"), default_timeout=180)
    at.run()
    check(at, "load awal")

    # --- pindah ke tab Prediction Lab (tab index 5) ---
    # streamlit AppTest tidak punya API klik-tab langsung; semua tab content
    # sudah dieksekusi saat run() (st.tabs merender semua isi tab sekaligus),
    # jadi widget di tab manapun sudah "ada" & bisa diuji langsung.

    # tombol sampel acak
    btn = [b for b in at.button if "Sampel acak" in b.label]
    assert btn, "tombol sampel acak tidak ditemukan"
    btn[0].click().run()
    check(at, "klik 'Sampel acak dari histori'")

    # tombol reset rata-rata
    btn = [b for b in at.button if "Reset ke rata-rata" in b.label]
    assert btn, "tombol reset tidak ditemukan"
    btn[0].click().run()
    check(at, "klik 'Reset ke rata-rata historis'")

    # geser salah satu slider komposisi ke ekstrem (uji clip Others & bounds warning)
    al2o3_slider = [s for s in at.slider if "Al₂O₃" in s.label]
    assert al2o3_slider, "slider Al2O3 tidak ditemukan"
    hi = al2o3_slider[0].max
    al2o3_slider[0].set_value(hi).run()
    check(at, f"slider Al2O3 -> maksimum ({hi})")

    # geser slider proses (digester temp) ke minimum
    dt_sliders = [s for s in at.slider if "Suhu Digester" in s.label]
    assert dt_sliders, "slider suhu digester tidak ditemukan"
    lo = dt_sliders[0].min
    dt_sliders[0].set_value(lo).run()
    check(at, f"slider suhu digester -> minimum ({lo})")

    # ganti target sensitivitas via selectbox
    sens_sel = [s for s in at.selectbox if s.key == "pl_sens_target"]
    assert sens_sel, "selectbox target sensitivitas tidak ditemukan"
    sens_sel[0].set_value("total_opex").run()
    check(at, "ganti target sensitivitas -> total_opex")

    # tombol latih ulang model
    retrain_btn = [b for b in at.button if b.key == "pl_retrain_btn"]
    assert retrain_btn, "tombol latih ulang tidak ditemukan"
    retrain_btn[0].click().run()
    check(at, "klik 'Latih Ulang Sekarang'")

    # --- overview: tombol regret & handover ---
    regret_btn = [b for b in at.button if "Hitung regret" in b.label]
    assert regret_btn, "tombol regret tidak ditemukan"
    regret_btn[0].click().run()
    check(at, "klik 'Hitung regret 8 jam terakhir'")

    handover_btn = [b for b in at.button if "laporan serah-terima" in b.label]
    assert handover_btn, "tombol handover tidak ditemukan"
    handover_btn[0].click().run()
    check(at, "klik 'Buat draf laporan serah-terima shift'")

    # ganti target/feature di korelasi overview
    corr_target = [s for s in at.selectbox if s.key == "ov_corr_target"]
    assert corr_target, "selectbox korelasi target tidak ditemukan"
    corr_target[0].set_value("red_mud_t").run()
    check(at, "ganti target korelasi -> red_mud_t")

    print("\n🎉 SEMUA INTERAKSI WIDGET BARU OK — tidak ada exception.")


if __name__ == "__main__":
    main()
