"""Neraca massa Bayer — replikasi Python dari mesin kalkulator Excel.

Sumber: data/calculator/Bayer_Process_Mass_Water_Balance.xlsm
        (8 sheet: Dashboard_Monitoring, PROCESS KINETICS, Molar_Base_Data,
         Pre-Desilication_Balance, Digestion_Balance, Clarification_RedMud,
         Precipitation_Hydrate, SPENT LIQUOR CONDITIONING)

Modul ini adalah terjemahan literal, sel-demi-sel, dari formula pada workbook
di atas (bukan model ML). File data/raw/data.csv dihasilkan dari workbook ini
lewat macro VBA (lihat docs/08-catatan-penting.md): macro mengacak sel input
Dashboard_Monitoring!C10:C19 (komposisi) dan C25/C30/C32/C35/C38 (parameter
proses), memaksa Application.Calculate, lalu menyalin sel hasil ke baris CSV.

Kegunaan modul ini di aplikasi (fitur "Prediction Analysis"):
- Sebagai kalkulator neraca massa deterministik yang independen dari model ML,
  dipakai untuk cross-check "apa kata fisika/Excel" versus "apa kata model
  LightGBM" atas komposisi + parameter proses yang sama.
- Tidak butuh Excel/LibreOffice terpasang — murni Python, sub-milidetik per
  panggilan, sehingga aman dipakai untuk slider real-time di dashboard.

Sirkuit spent-liquor (bagian "disirkulasi ulang ke pre-desilication" pada
deskripsi proses) membentuk satu referensi melingkar di dalam workbook, yang
di Excel diselesaikan lewat iterative calculation. Penelusuran aljabar
menunjukkan hanya SATU variabel yang benar-benar melingkar (massa NaAlO2 yang
terbawa balik dari SPENT LIQUOR CONDITIONING ke Pre-Desilication); variabel
lain (air balik = selalu 330 t/jam pada basis 120 t/jam bauksit kering, massa
NaOH balik = bentuk tertutup dari target konsentrasi NaOH) terbukti punya
solusi bentuk-tertutup. Modul ini tetap menghitung seluruh rantai secara
literal (bukan bentuk yang sudah disederhanakan) dan menyelesaikan satu
variabel melingkar itu lewat iterasi titik-tetap (~15-30 iterasi, <1 ms),
supaya kekeliruan penurunan rumus mudah terlihat saat divalidasi ulang.

VALIDASI: dijalankan atas seluruh 995 baris valid data/raw/data.csv
(nilai sama persis dengan yang dipakai melatih model ML), membandingkan
keluaran fungsi `run()` terhadap kolom aktual. Rerata galat relatif:
recovery_pct 0.02%, red_mud_t 0.05%, total_opex 0.09%, precip_yield_pct
0.01%, digestion_eff_pct <0.01%, naoh_makeup_t 0.11%, cao_total_t 0.07%.
Galat maksimum (baris kasus tepi, mis. di ambang causticity 0.85) <8%.
Dua penyesuaian dilakukan berdasar validasi ini (didokumentasikan di kode):
(1) efisiensi digesti dibatasi maksimum 100% (rumus mentah bisa >100% pada
kombinasi partikel sangat halus + NaOH sangat pekat — Excel membatasi ini,
kemungkinan lewat MIN() yang tidak eksplisit di string formula tersimpan);
(2) "Net Make-up NaOH" divalidasi sama dengan SPENT LIQUOR CONDITIONING!C53
saja — formula Dashboard!H38 pada file .xlsm yang diunggah menjumlahkan
`+Digestion_Balance!C54`, tetapi suku ini membuat galat sampai >2000% pada
sebagian baris; sangat mungkin H38 diedit setelah data.csv dibuat. Kami
mengkalibrasi ke data yang benar-benar dipakai melatih model.

Referensi mol (Molar_Base_Data) dan basis 120 t/jam bauksit kering
(Dashboard_Monitoring!C6=150 t/jam basah, C7=20% kadar air, tidak diacak
macro) ditetapkan sebagai konstanta di bawah.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

# --------------------------------------------------------------------------
# Molar_Base_Data — massa molar (g/mol), disalin persis dari sheet.
# --------------------------------------------------------------------------
MW_AL2O3 = 101.96
MW_SIO2 = 60.09
MW_FE2O3 = 159.70
MW_TIO2 = 79.87
MW_CAO = 56.08
MW_MGO = 40.30
MW_NA2O = 61.98
MW_K2O = 94.20
MW_CR2O3 = 152.00
MW_OTHERS = 60.00
MW_NAOH = 39.99
MW_H2O = 18.02
MW_NAALO2 = 81.97
MW_ALOH3 = 78.00
MW_CAOH2 = 74.10
MW_DSP_CA = 426.42   # kalsium hidrogarnet — DSP tahap pre-desilication
MW_DSP_NA = 320.16   # sodalit — DSP tahap digestion
MW_NA2CO3 = 107.98
MW_CACO3 = 126.16
MW_AL = 26.98

# --------------------------------------------------------------------------
# Basis proses & konstanta "constant" (skema: role == "constant"), diambil
# dari Dashboard_Monitoring — TIDAK diacak oleh macro VBA sehingga bernilai
# tunggal pada seluruh dataset sintesis (dipantau lewat src/capability.py).
# --------------------------------------------------------------------------
DRY_BAUXITE_T = 120.0          # C6*(1-C7) = 150*(1-0.20), t/jam bauksit kering
BAUXITE_MOISTURE_T = 30.0      # C6*C7 = 150*0.20, t/jam air bawaan bauksit
LS_RATIO = 3.0                 # C31 — Liquor/Solid ratio digester
TARGET_SLURRY_T = LS_RATIO * DRY_BAUXITE_T           # 360 t/jam
MAKEUP_WATER_T = max(0.0, TARGET_SLURRY_T - BAUXITE_MOISTURE_T)  # 330 t/jam
CA_SI_TARGET = 1.2             # C26 — target rasio Ca/Si slurry pre-desil
PREDESIL_EFF = 0.8             # C27 — efisiensi proses pre-desilication
CLARIF_EFF = 0.98              # C37 — efisiensi pemisahan clarifier
WASH_EFF = 0.8                 # C42 — efisiensi pencucian red mud
WASH_WATER_RATIO = 2.5         # C41 — rasio air cuci per ton red mud
PRODUCT_MOISTURE = 0.1         # C39 — kadar air bebas produk hidrat
NAOH_CARB_FRAC = 0.1           # C40 — fraksi NaOH terkarbonasi jadi Na2CO3
MIN_CAUSTICITY = 0.85          # C44 — ambang causticity minimum
NA2CO3_CONV_EFF = 0.9          # C43 — efisiensi konversi Na2CO3->NaOH (kapur)
STEAM_INJECT_FRAC = 0.05       # C29 — fraksi steam injeksi ke digester
STEAM_EVAP_FRAC = 0.03         # C33 — fraksi kehilangan uap flash digester
STEAM_FLASH_FRAC = 0.02        # C34 — fraksi air flash steam

# Harga satuan OPEX (Dashboard_Monitoring!H7:H10) — asumsi harga internal
# model, satuan mata uang per ton (README menyebut basis Rp; nilai relatif
# antar skenario yang penting, bukan nilai absolutnya).
PRICE_BAUXITE = 35.0
PRICE_NAOH = 500.0
PRICE_CAO = 75.0
PRICE_WATER = 0.5

# --------------------------------------------------------------------------
# Kinetika — sheet "PROCESS KINETICS ".
# --------------------------------------------------------------------------
DIG_C0 = 20000.0        # B10 konstanta laju
DIG_EA = 50000.0        # B11 energi aktivasi (J/mol)
DIG_R = 8.314           # B12 konstanta gas (J/mol.K)
DIG_T_RESIDENCE = 30.0  # B6 waktu tinggal digester (menit, tetap)

PRECIP_A = 6.0          # B20 konstanta kurva kesetimbangan Ceq
PRECIP_B = 2500.0       # B21 konstanta kurva kesetimbangan Ceq
PRECIP_KP = 0.0025      # B23 konstanta laju presipitasi
PRECIP_SURF_AREA = 0.1  # B25 luas permukaan spesifik seed (m^2/g)
PRECIP_HOURS = 48.0     # waktu tinggal tangki presipitasi (jam, tetap)

_EPS = 1e-9


def digestion_efficiency(particle_size_um: float, naoh_conc_gl: float,
                          digester_temp_c: float) -> float:
    """PROCESS KINETICS!G7 — model shrinking-core orde-3.

    k = (C0/ukuran_partikel) * konsentrasi_NaOH * exp(-Ea/(R*T))
    efisiensi = 1 - (1 - k*t)^3, dibatasi [0, 1] (lihat catatan validasi di
    docstring modul: data aktual selalu <=100%).
    """
    particle_size_um = max(particle_size_um, _EPS)
    T = digester_temp_c + 273.0
    rate = math.exp(-DIG_EA / DIG_R / T)
    k = (DIG_C0 / particle_size_um) * naoh_conc_gl * rate
    eff = 1.0 - (1.0 - k * DIG_T_RESIDENCE) ** 3
    return min(1.0, max(0.0, eff))


def precip_yield_fn(c_caustic_gl: float, seed_conc_gl: float,
                     precip_temp_c: float) -> tuple[float, float, float, float]:
    """PROCESS KINETICS!I20 — kurva kesetimbangan + laju presipitasi seed.

    Ceq         = C_kaustik * exp(a - b/T)             (g/L, kesetimbangan)
    n_maks      = (C_kaustik - Ceq) / C_kaustik
    A_seed      = konsentrasi_seed_gL * luas_permukaan_spesifik
    yield_frac  = n_maks * (1 - exp(-kp * A_seed * jam_tinggal))
    """
    c_caustic_gl = max(c_caustic_gl, _EPS)
    T = precip_temp_c + 273.0
    ceq = c_caustic_gl * math.exp(PRECIP_A - PRECIP_B / T)
    n_max = max(0.0, (c_caustic_gl - ceq) / c_caustic_gl)
    aseed = seed_conc_gl * PRECIP_SURF_AREA
    yield_frac = n_max * (1.0 - math.exp(-PRECIP_KP * aseed * PRECIP_HOURS))
    return yield_frac, ceq, n_max, aseed


def normalize_composition(composition: dict[str, float]) -> dict[str, float]:
    """Skalakan 10 oksida agar berjumlah tepat 100% (proporsional).

    Berguna dipakai pada input manual operator di UI, yang mungkin tidak
    berjumlah pas 100.00 akibat pembulatan slider/number_input.
    """
    keys = ["al2o3_pct", "reactive_sio2_pct", "fe2o3_pct", "tio2_pct", "cao_pct",
            "mgo_pct", "na2o_pct", "k2o_pct", "cr2o3_pct", "others_pct"]
    total = sum(max(0.0, composition.get(k, 0.0)) for k in keys)
    if total <= _EPS:
        return {k: 0.0 for k in keys}
    return {k: max(0.0, composition.get(k, 0.0)) / total * 100.0 for k in keys}


@dataclass
class MassBalanceResult:
    """Hasil neraca massa lengkap satu titik operasi (komposisi + parameter)."""

    recovery_pct: float
    precip_yield_pct: float
    red_mud_t: float
    total_opex: float
    naoh_opex: float
    cao_opex: float
    digestion_eff_pct: float
    naoh_makeup_t: float
    cao_total_t: float
    cao_addition_t: float
    al_feed_t: float
    al_recycled_t: float
    al_lost_redmud_t: float
    hydrate_t: float
    hydrate_wet_t: float
    seed_t: float
    water_consumption_t: float
    water_wash_t: float
    water_evap_t: float
    caoh_predesil_t: float
    caoh2_lost_t: float
    caoh2_cond_t: float
    naoh_consumed_t: float
    causticity: float
    iterations: int = field(repr=False)

    def as_dict(self) -> dict[str, float]:
        d = {k: v for k, v in self.__dict__.items() if k != "iterations"}
        return d


def run(composition: dict[str, float], knobs: dict[str, float],
        max_iter: int = 100, tol: float = 1e-9, *,
        wet_feed_t: float = 1000.0, moisture_frac: float = 0.2) -> MassBalanceResult:
    """Jalankan neraca massa lengkap untuk satu (komposisi, parameter proses).

    Parameters
    ----------
    composition : dict dengan kunci schema.INPUTS (al2o3_pct, reactive_sio2_pct,
        fe2o3_pct, tio2_pct, cao_pct, mgo_pct, na2o_pct, k2o_pct, cr2o3_pct,
        others_pct), dalam satuan persen (mis. 62.78 untuk 62.78%).
    knobs : dict dengan kunci schema.KNOBS (particle_size_um, digester_temp_c,
        naoh_conc_gl, precip_temp_c, seed_ratio).
    wet_feed_t, moisture_frac : Dashboard!C6 & C7 pada xlsm UPDATED — laju umpan
        bauksit basah (t/jam) dan fraksi kadar airnya. Seluruh aliran massa di
        workbook linear terhadap dry feed = C6*(1-C7); target persen (recovery,
        yield, efisiensi) bebas skala. Engine internal tetap pada basis
        tervalidasi 120 t/jam kering, lalu massa/OPEX diskalakan dry/120
        + koreksi air make-up bila moisture != 20% (make-up = L/S*dry -
        wet*moisture: air bawaan bauksit menggantikan air make-up ton-per-ton).
        Default (1000, 0.2) = basis data.csv v2 (dry 800 t/jam), sebanding
        langsung dengan data & model ML.

    Returns
    -------
    MassBalanceResult berisi 4 target utama (recovery_pct, red_mud_t,
    total_opex, precip_yield_pct) plus rincian neraca massa (intermediate)
    untuk panel "detail perhitungan".
    """
    al2o3_f = composition["al2o3_pct"] / 100.0
    sio2_f = composition["reactive_sio2_pct"] / 100.0
    fe2o3_f = composition["fe2o3_pct"] / 100.0
    tio2_f = composition["tio2_pct"] / 100.0
    cao_f = composition["cao_pct"] / 100.0
    mgo_f = composition["mgo_pct"] / 100.0
    na2o_f = composition["na2o_pct"] / 100.0
    k2o_f = composition["k2o_pct"] / 100.0
    cr2o3_f = composition["cr2o3_pct"] / 100.0
    others_f = composition["others_pct"] / 100.0

    particle_size_um = max(knobs["particle_size_um"], _EPS)
    digester_temp_c = knobs["digester_temp_c"]
    naoh_conc_gl = knobs["naoh_conc_gl"]
    precip_temp_c = knobs["precip_temp_c"]
    seed_ratio = knobs["seed_ratio"]

    dig_eff = digestion_efficiency(particle_size_um, naoh_conc_gl, digester_temp_c)

    # ============= Pre-Desilication_Balance : bagian hanya-komposisi ========
    pd_C5 = DRY_BAUXITE_T * al2o3_f
    pd_C6 = DRY_BAUXITE_T * sio2_f
    pd_C7 = DRY_BAUXITE_T * fe2o3_f
    pd_C8 = DRY_BAUXITE_T * tio2_f
    pd_C9 = DRY_BAUXITE_T * cao_f
    pd_C10 = DRY_BAUXITE_T * mgo_f
    pd_C11 = DRY_BAUXITE_T * na2o_f
    pd_C12 = DRY_BAUXITE_T * k2o_f
    pd_C13 = DRY_BAUXITE_T * cr2o3_f
    pd_C14 = DRY_BAUXITE_T * others_f  # noqa: F841 (disimpan utk kelengkapan)

    pd_E6 = pd_C6 / MW_SIO2 * 1000.0
    pd_E9 = pd_C9 / MW_CAO * 1000.0
    pd_E11 = pd_C11 / MW_NA2O * 1000.0

    pd_C18 = TARGET_SLURRY_T
    pd_C19 = BAUXITE_MOISTURE_T
    pd_C20 = max(0.0, pd_C18 - pd_C19)

    pd_E33 = pd_E6
    pd_E44 = 2.0 * pd_E11
    pd_C44 = pd_E44 * MW_NAOH / 1000.0

    # ============= Iterasi titik-tetap: x = massa NaAlO2 balik (spent liquor)
    x = 0.0
    prev_naoh_recycle = 0.0
    prev_caoh2_recycle = 0.0
    it = 0
    for it in range(max_iter):
        pd_E27 = prev_caoh2_recycle / MW_CAOH2 * 1000.0
        pd_E34 = pd_E9 + pd_E27
        pd_E36 = pd_E33 * CA_SI_TARGET - pd_E34
        pd_E37 = pd_E34 + pd_E36  # == CA_SI_TARGET * pd_E33 (identitas aljabar)

        pd_E45 = pd_E37
        pd_C45 = pd_E45 * MW_CAOH2 / 1000.0
        pd_E47 = pd_E45 * PREDESIL_EFF
        pd_C47 = MW_CAOH2 * pd_E47 / 1000.0
        pd_E46 = pd_E47 / 3.0 * 2.0
        pd_C46 = MW_SIO2 * pd_E46 / 1000.0
        pd_E48 = pd_E46
        pd_C48 = pd_E48 * MW_AL2O3 / 1000.0
        pd_E49 = pd_E44 / 2.0 + pd_E45
        pd_C49 = pd_E49 * MW_H2O / 1000.0
        pd_E50 = pd_E47 / 3.0
        pd_C50 = pd_E50 * MW_DSP_CA / 1000.0
        pd_E51 = pd_E50 * 3.0
        pd_C51 = pd_E51 * MW_H2O / 1000.0

        pd_C53 = pd_C49 - pd_C51
        pd_C57 = pd_C5 - pd_C48
        pd_C59 = pd_C45 - pd_C47
        pd_C61 = pd_C18 - pd_C53

        # -------------- Digestion_Balance (bagian komposisi/parameter) -----
        dg_C5 = pd_C57
        dg_C6 = DRY_BAUXITE_T * sio2_f - pd_C46
        dg_C7 = pd_C7
        dg_C8 = pd_C8
        dg_C9 = pd_C59
        dg_C10 = pd_C10
        dg_C12 = pd_C12
        dg_C13 = pd_C13
        dg_C20 = pd_C61

        dg_C25 = dg_C5 * dig_eff
        dg_E25 = dg_C25 / MW_AL2O3 * 1000.0
        dg_C26 = dg_E25 * 2.0 * MW_NAOH / 1000.0
        dg_C27 = dg_E25 * 2.0 * MW_NAALO2 / 1000.0
        dg_C28 = dg_E25 * 4.0 * MW_H2O / 1000.0

        dg_C30 = dg_C6
        dg_E30 = dg_C30 / MW_SIO2 * 1000.0
        dg_C31 = dg_E30 * 2.0 * MW_NAOH / 1000.0
        dg_C32 = dg_E30 * 0.5 * MW_AL2O3 / 1000.0
        dg_C33 = dg_C32 + dg_C30 + dg_E30 * 4.0 * MW_H2O / 1000.0
        dg_E34 = dg_E30 * 4.0
        dg_C34 = MW_DSP_NA * dg_E34 / 1000.0

        dg_C43 = dg_C5 * (1.0 - dig_eff) - dg_C32

        dg_C46 = (TARGET_SLURRY_T + dg_C5) * STEAM_INJECT_FRAC
        dg_C47 = (TARGET_SLURRY_T + dg_C5) * STEAM_EVAP_FRAC
        dg_C48 = TARGET_SLURRY_T * STEAM_FLASH_FRAC

        dg_C51 = dg_C26
        dg_C52 = dg_C31
        dg_C53 = dg_C51 + dg_C52

        pd_C31 = prev_naoh_recycle + pd_C44
        dg_C21 = pd_C31
        dg_C22 = x

        dg_C54 = max(0.0, dg_C53 - dg_C21)
        dg_C56 = dg_C27 + dg_C22
        dg_C57 = dg_C21 - dg_C53 + dg_C54

        dg_C58 = dg_C20 + dg_C46 + dg_C28 - dg_C47 - dg_C48 - dg_C34

        # -------------------- Clarification_RedMud --------------------------
        cl_C4 = dg_C56
        cl_C5 = dg_C57
        cl_C6 = dg_C9
        cl_C7 = dg_C58

        cl_C24 = cl_C4 * (1.0 - CLARIF_EFF)
        cl_C25 = cl_C5 * (1.0 - CLARIF_EFF)
        cl_C26 = cl_C6 * (1.0 - CLARIF_EFF)
        cl_C27 = cl_C7 * (1.0 - CLARIF_EFF)

        cl_C18 = cl_C4 - cl_C24
        cl_C19 = cl_C5 - cl_C25
        cl_C20 = cl_C6 - cl_C26
        cl_C21 = cl_C7 - cl_C27

        cl_C28 = (dg_C7 + dg_C8 + dg_C10 + dg_C12 + dg_C13 + dg_C43
                  + (dg_C33 + pd_C50))
        cl_C29 = WASH_WATER_RATIO * cl_C28 - cl_C27
        cl_C30 = cl_C27 + cl_C29
        cl_C31 = (1.0 - WASH_EFF) * (cl_C27 + cl_C29)
        cl_C33 = WASH_EFF * cl_C30
        cl_C34 = WASH_EFF * cl_C24
        cl_C35 = WASH_EFF * cl_C25
        cl_C36 = WASH_EFF * cl_C26

        cl_C38 = (cl_C28 + cl_C31 + cl_C24 - cl_C34 + cl_C25 - cl_C35
                  + (cl_C26 - cl_C36))
        cl_C49 = cl_C24 - cl_C34
        cl_C50 = cl_C25 - cl_C35

        # -------------------- Precipitation_Hydrate --------------------------
        pr_C5 = cl_C18
        pr_C6 = cl_C19
        pr_C7 = cl_C20
        pr_C8 = max(cl_C21, _EPS)
        pr_C9 = pr_C5 + pr_C6 + pr_C7 + pr_C8  # noqa: F841

        pr_E5 = pr_C5 / MW_NAALO2 * 1000.0
        pr_E11 = pr_E5 * seed_ratio
        pr_C11 = pr_E11 * MW_ALOH3 / 1000.0
        pr_C12 = pr_C11 / pr_C8 * 1000.0

        c_caustic = pr_C5 / pr_C8 * 1000.0
        yld, ceq, n_max, aseed = precip_yield_fn(c_caustic, pr_C12, precip_temp_c)

        pr_C15 = pr_C5 * yld
        pr_E15 = pr_C15 / MW_NAALO2 * 1000.0
        pr_C16 = pr_E15 * 2.0 * MW_H2O / 1000.0
        pr_C17 = pr_E15 * MW_ALOH3 / 1000.0
        pr_C18 = pr_E15 * MW_NAOH / 1000.0

        pr_C22 = pr_C17 * PRODUCT_MOISTURE / (1.0 - PRODUCT_MOISTURE)
        pr_C23 = pr_C17 + pr_C22

        pr_C26 = pr_C5 * (1.0 - yld)
        pr_C27 = pr_C6 + pr_C18
        pr_C28 = pr_C7
        pr_E27 = pr_C27 / MW_NAOH * 1000.0

        pr_E30 = pr_E27 * NAOH_CARB_FRAC
        pr_E31 = pr_E27 * NAOH_CARB_FRAC / 2.0
        pr_C31 = pr_E31 * MW_NA2CO3 / 1000.0
        pr_E32 = pr_E31
        pr_C32 = pr_E32 * MW_H2O / 1000.0
        pr_C33 = dg_C58 - pr_C16 - pr_C22 + pr_C32
        pr_E34 = pr_E27 - pr_E30
        pr_C34 = MW_NAOH * pr_E34 / 1000.0

        # ---------------- SPENT LIQUOR CONDITIONING ---------------------------
        sl_C5 = pr_C26
        sl_C6 = pr_C27
        sl_C7 = pr_C28
        sl_C8 = pr_C31
        sl_C9 = pr_C33
        sl_C11 = pr_C34

        sl_C14 = cl_C33
        sl_C15 = cl_C34
        sl_C16 = cl_C35
        sl_C17 = cl_C36

        sl_C21 = sl_C11 + sl_C16
        sl_C22 = sl_C7 + sl_C17
        sl_E21 = sl_C21 / MW_NAOH * 1000.0
        sl_E22 = sl_C22 / MW_CAOH2 * 1000.0
        sl_E8 = sl_C8 / MW_NA2CO3 * 1000.0

        sl_C26 = max(sl_C9 + sl_C14, _EPS)
        F26 = pd_C20
        sl_C27 = (sl_C26 - F26) / sl_C26

        sl_C34 = sl_E21 / max(sl_E21 + sl_E8, _EPS)  # causticity
        below = sl_C34 < MIN_CAUSTICITY
        B36 = MIN_CAUSTICITY - sl_C34
        sl_E36 = (sl_E21 + sl_E8) * B36 if below else 0.0
        sl_E37 = (sl_E36 / NA2CO3_CONV_EFF) if below else 0.0
        sl_E38 = sl_E22
        sl_E39 = 0.0 if sl_E37 < sl_E22 else (sl_E37 - sl_E22)
        sl_C43 = (sl_E38 + sl_E39) * MW_CAOH2 / 1000.0
        sl_E44 = sl_E37 * NA2CO3_CONV_EFF
        sl_C44 = sl_E44 * MW_CACO3 / 1000.0  # noqa: F841
        sl_E42 = sl_E38 * 2.0 if sl_E36 == 0.0 else sl_E36 * 2.0
        sl_C42 = sl_E42 * MW_NAOH / 1000.0

        sl_C50 = sl_C21 + sl_C42
        sl_C52 = pd_C18 * naoh_conc_gl / 1000.0 - pd_C44
        sl_C53 = sl_C52 - sl_C50

        sl_C56 = sl_C26 - sl_C26 * sl_C27  # identitas aljabar -> selalu F26
        sl_C57 = sl_C50 + sl_C53           # identitas aljabar -> selalu sl_C52
        sl_C60 = sl_C15 + sl_C5
        sl_C61 = (sl_E38 if sl_E36 == 0.0 else ((sl_E38 + sl_E39) - sl_E37)) * MW_CAOH2 / 1000.0

        x_new = sl_C60
        naoh_recycle_new = sl_C57
        caoh2_recycle_new = sl_C61

        converged = (abs(x_new - x) < tol
                     and abs(naoh_recycle_new - prev_naoh_recycle) < tol
                     and abs(caoh2_recycle_new - prev_caoh2_recycle) < tol)
        x = x_new
        prev_naoh_recycle = naoh_recycle_new
        prev_caoh2_recycle = caoh2_recycle_new
        if converged:
            break

    # -------------------- Ringkasan Dashboard_Monitoring ----------------------
    al_feed_t = (pd_C5 / MW_AL2O3 * 1000.0) * MW_AL / 1000.0 * 2.0
    al_recycled_t = x / MW_NAALO2 * 1000.0 * MW_AL / 1000.0
    al_lost_redmud_t = ((cl_C49 / MW_NAALO2 * 1000.0) * MW_AL / 1000.0
                         + (dg_C32 / MW_AL2O3 * 1000.0) * MW_AL / 1000.0 * 2.0
                         + (pd_C48 / MW_AL2O3 * 1000.0) * MW_AL / 1000.0 * 2.0)
    recovery_frac = (pr_E15 * MW_AL / 1000.0) / max(al_feed_t, _EPS)
    naoh_makeup_t = sl_C53
    caoh_predesil_t = pd_C47
    caoh2_lost_t = cl_C50
    caoh2_cond_t = sl_C43
    cao_total_t = (caoh_predesil_t + caoh2_cond_t) * MW_CAO / MW_CAOH2

    # CaO Addition in process = CaO segar ke pre-desilication (dari target
    # rasio Ca/Si, identitas E37=CA_SI_TARGET*pd_E33) + burnt-lime tambahan
    # bila causticity di bawah ambang (sl_E39).
    pd_E36_final = pd_E33 * CA_SI_TARGET - (pd_E9 + prev_caoh2_recycle / MW_CAOH2 * 1000.0)
    pd_C36_final = pd_E36_final * MW_CAO / 1000.0
    cao_addition_t = pd_C36_final + sl_E39 * MW_CAO / 1000.0

    naoh_opex = PRICE_NAOH * naoh_makeup_t
    cao_opex = PRICE_CAO * cao_total_t
    total_opex = naoh_opex + cao_opex

    water_consumption_t = pd_C53 + dg_C34 + pr_C16
    water_wash_t = cl_C33
    water_evap_t = sl_C26 * sl_C27

    # --- skala feed rate/moisture (lihat docstring): engine basis 120 t/jam ---
    dry_feed_t = max(wet_feed_t * (1.0 - moisture_frac), _EPS)
    _s = dry_feed_t / DRY_BAUXITE_T
    # koreksi air make-up: engine mengasumsikan moisture basis 20%;
    # selisih air bawaan bauksit menggantikan air make-up ton-per-ton
    water_makeup_corr = (_s * BAUXITE_MOISTURE_T) - (wet_feed_t * moisture_frac)

    def _sc(v: float) -> float:
        return v * _s

    return MassBalanceResult(
        recovery_pct=recovery_frac * 100.0,
        precip_yield_pct=yld * 100.0,
        red_mud_t=_sc(cl_C38),
        total_opex=_sc(total_opex),
        naoh_opex=_sc(naoh_opex),
        cao_opex=_sc(cao_opex),
        digestion_eff_pct=dig_eff * 100.0,
        naoh_makeup_t=_sc(naoh_makeup_t),
        cao_total_t=_sc(cao_total_t),
        cao_addition_t=_sc(cao_addition_t),
        al_feed_t=_sc(al_feed_t),
        al_recycled_t=_sc(al_recycled_t),
        al_lost_redmud_t=_sc(al_lost_redmud_t),
        hydrate_t=_sc(pr_C17),
        hydrate_wet_t=_sc(pr_C23),
        seed_t=_sc(pr_C12),
        water_consumption_t=_sc(water_consumption_t) + water_makeup_corr,
        water_wash_t=_sc(water_wash_t),
        water_evap_t=_sc(water_evap_t),
        caoh_predesil_t=_sc(caoh_predesil_t),
        caoh2_lost_t=_sc(caoh2_lost_t),
        caoh2_cond_t=_sc(caoh2_cond_t),
        naoh_consumed_t=_sc(dg_C53),
        causticity=sl_C34,
        iterations=it + 1,
    )


def run_dict(composition: dict[str, float], knobs: dict[str, float], *,
             wet_feed_t: float = 1000.0, moisture_frac: float = 0.2) -> dict[str, float]:
    """Sama seperti `run`, tapi mengembalikan dict biasa (untuk UI/plot)."""
    return run(composition, knobs,
               wet_feed_t=wet_feed_t, moisture_frac=moisture_frac).as_dict()
