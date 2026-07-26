# 20 — Diagram Arsitektur (Visual)

> ⚠️ **DOKUMEN INI MENDAHULUI PENSIUNNYA STREAMLIT.**
> Konsol Streamlit sudah dikeluarkan dari `main` — UI sekarang **Next.js + React**
> (`frontend/`) di atas REST API yang sama. Semua instruksi `streamlit run
> app/main.py` di bawah **tidak lagi berlaku di `main`**; ia tetap berjalan di
> branch arsip `feat/old-ada-streamlit`. Cara menjalankan & deploy yang berlaku
> sekarang ada di [README](../README.md).
> Isi dokumen ini sengaja dibiarkan utuh sebagai catatan sejarah keputusan tim.

> Pelengkap visual untuk [09-arsitektur-v2.md](09-arsitektur-v2.md) (prinsip P1–P6
> & struktur kode) dan [07-integrasi-produksi.md](07-integrasi-produksi.md) (tier
> integrasi). Dokumen ini **tidak menambah klaim baru** — hanya menggambarkan
> yang sudah ada di kode agar cepat dipahami. Semua diagram Mermaid: render di
> GitHub, VS Code (ekstensi Markdown Preview Mermaid), dan Obsidian tanpa alat
> eksternal.

Daftar diagram:
1. [Konteks sistem (siapa memakai apa)](#1-konteks-sistem)
2. [Arsitektur headless — satu otak, dua wajah](#2-arsitektur-headless)
3. [Struktur modul inti Python](#3-struktur-modul-inti)
4. [Alur data: mentah → prediksi → advisory](#4-alur-data)
5. [Neuro-symbolic: ML + fisika + optimizer + expert](#5-neuro-symbolic)
6. [Capability detection (fitur nyala/mati)](#6-capability-detection)
7. [Sequence: satu siklus advisory](#7-sequence-advisory)
8. [Roadmap integrasi produksi (3 tier)](#8-roadmap-integrasi)

---

## 1. Konteks sistem

Siapa dan sistem luar apa yang berinteraksi dengan OptiBayer (C4 — level Context).

```mermaid
flowchart TB
    CRO["👷 Control Room Operator<br/>(pengguna utama)"]
    SUP["🧑‍💼 Supervisor / Insinyur Proses"]

    subgraph OB["OptiBayer — CRO Advisory Console"]
      CORE["Inti headless (Python)<br/>ML + Fisika + Optimizer + Advisory"]
    end

    DATA[("Data proses Bayer<br/>CSV sintesis → historian pabrik")]
    LLM["Penyedia LLM (opsional)<br/>template / Ollama / Groq / Gemini"]
    DCS["Sistem pabrik: DCS / OPC UA / MQTT<br/>(read-only — roadmap produksi)"]

    CRO -->|memantau, terima/tolak advisory| OB
    SUP -->|tambah SOP ke Knowledge, audit| OB
    DATA -->|adapter → skema kanonik| CORE
    CORE -.->|membahasakan angka<br/>tanpa mengarang| LLM
    DCS -.->|tarik telemetri READ-ONLY| CORE

    classDef sys fill:#c9a24a22,stroke:#c9a24a,color:#111;
    classDef ext fill:#eee,stroke:#999,color:#111;
    class OB,CORE sys;
    class DATA,LLM,DCS ext;
```

**Poin keamanan (doc 07):** panah ke DCS **read-only** — dashboard tak pernah
menulis perintah ke aktuator pabrik. LLM hanya *membahasakan* angka yang sudah
dihitung; tidak menjadi sumber angka.

---

## 2. Arsitektur headless

Satu inti Python dipakai oleh **dua frontend** lewat kontrak yang sama —
bukti desain data-agnostic (P1–P6 doc 09).

```mermaid
flowchart LR
    subgraph FE["Antarmuka (klien)"]
      ST["Streamlit<br/>app/ — cepat & lengkap"]
      NX["Next.js + React<br/>frontend/ — UI produksi"]
    end

    subgraph API["Kontrak tunggal"]
      CT["contract.py<br/>ENDPOINTS = data"]
      REST["REST API (FastAPI)<br/>src/integration/api.py"]
      MCP["MCP server<br/>(roadmap, def sama)"]
    end

    subgraph CORE["Inti headless — src/"]
      PR["models/ (ML)"]
      PH["physics/ (deterministik)"]
      OP["optimize/ (NSGA-II)"]
      AD["advisory/ (grounded)"]
      KN["advisory/knowledge (expert)"]
    end

    ST -->|in-process| CORE
    NX -->|HTTP| REST
    REST --> CT
    MCP -.-> CT
    CT --> CORE

    classDef core fill:#c9a24a22,stroke:#c9a24a,color:#111;
    class PR,PH,OP,AD,KN core;
```

> **Kenapa ini nilai jual:** menambah/ mengganti frontend (atau menambah MCP
> untuk agen AI) **tidak menyentuh logika** — semua lewat `contract.py` yang
> mendefinisikan endpoint sebagai *data*, bukan kode ter-duplikasi.

---

## 3. Struktur modul inti

Tiap paket punya satu tanggung jawab; panah = arah ketergantungan.

```mermaid
flowchart TD
    SC["schema.py<br/>P1 · nama kolom kanonik + ROLE"]

    subgraph data["data/"]
      AD1["adapters.py<br/>P2 · CSV→kanonik"]
      VAL["validate.py"]
      RP["replay.py"]
    end
    CAP["capability.py<br/>P3 · fitur ON/OFF"]

    subgraph models["models/"]
      TR["train.py"]
      RG["registry.py<br/>P5 · model+metadata"]
      PRd["predict.py<br/>pintu tunggal ML"]
      EX["explain.py · SHAP"]
    end
    subgraph physics["physics/"]
      MB["mass_balance.py"]
      NA["na_balance.py"]
      CB["carbonation.py"]
      PC["precipitation.py"]
    end
    subgraph optimize["optimize/"]
      PA["pareto.py · NSGA-II"]
      GS["goal_seek.py"]
      RGr["regret.py"]
    end
    subgraph advisory["advisory/"]
      CTX["context.py"]
      PRV["providers.py<br/>P6 · LLM/template"]
      KNw["knowledge.py"]
    end

    SC --> AD1 --> VAL --> CAP
    CAP --> TR --> RG --> PRd --> EX
    PRd --> PA --> GS
    PA --> RGr
    PRd --> CTX
    MB --> CTX
    EX --> CTX
    CTX --> PRV
    KNw --> PRV

    classDef p fill:#199e7022,stroke:#199e70,color:#111;
    class MB,NA,CB,PC p;
```

Fisika (hijau) **tidak bergantung** pada ML — deterministik & unit-testable
(P4). Inilah "symbolic" pada neuro-symbolic.

---

## 4. Alur data

Dari file mentah sampai kartu advisory di layar.

```mermaid
flowchart LR
    RAW[("CSV mentah<br/>cp1252, ';', koma")]
    -->|adapters.py| CANON[("DataFrame kanonik<br/>bersih, numerik")]
    -->|capability.py| FLAG{"kolom<br/>bervariasi?"}

    FLAG -->|ya| TRAIN["train surrogate<br/>(LightGBM)"]
    FLAG -->|tidak| OFF["fitur OFF<br/>(mis. soft-sensor causticity)"]

    TRAIN --> REG[("registry<br/>model + bounds + metrik")]
    CANON -->|replay.py| SEQ["deret jam + gangguan<br/>(mis. Silika Spike)"]

    SEQ --> PRED["predict.py → target<br/>recovery, OPEX, red mud, yield"]
    REG --> PRED
    SEQ --> PHYS["physics → neraca massa,<br/>Na, karbonasi, Ceq"]

    PRED --> CTX["context.py<br/>(angka + SHAP + alarm)"]
    PHYS --> CTX
    OPT["optimize → setpoint terbaik"] --> CTX
    PRED --> OPT
    CTX --> ADV["advisory → Kartu<br/>Dampak / Tindakan / Kenapa"]
    ADV --> UI["Dashboard (Streamlit / Next.js)"]
```

---

## 5. Neuro-symbolic

Tiga sumber kecerdasan yang saling menjaga — bukan black-box tunggal.

```mermaid
flowchart TB
    subgraph N["🧠 Neural (belajar dari data)"]
      ML["Surrogate LightGBM<br/>recovery · OPEX · red mud · yield"]
      SHAP["SHAP<br/>faktor pendorong"]
    end
    subgraph S["📐 Symbolic (hukum & aturan)"]
      PHY["Kalkulator fisika<br/>neraca massa (Excel-grounded)"]
      OPTz["NSGA-II carbon-aware<br/>optimasi multi-objektif"]
    end
    subgraph E["📚 Expert (pengetahuan pabrik)"]
      KP["Knowledge Pack<br/>SOP ber-tag, wajib disitasi"]
    end

    ML --> DEC{"Advisory<br/>ter-grounding"}
    SHAP --> DEC
    PHY --> DEC
    OPTz --> DEC
    KP --> DEC
    DEC --> CARD["Kartu advisory + audit trail"]

    ML -. "validasi silang<br/>(anomali > 3σ)" .- PHY

    classDef n fill:#3987e522,stroke:#3987e5,color:#111;
    classDef s fill:#199e7022,stroke:#199e70,color:#111;
    classDef e fill:#c9a24a22,stroke:#c9a24a,color:#111;
    class ML,SHAP n;
    class PHY,OPTz s;
    class KP e;
```

**Jaring pengaman:** saat input di luar rentang latih (ekstrapolasi), UI menandai
prediksi ML kurang tepercaya sementara **kalkulator fisika tetap berlaku penuh**
(deterministik). ML dan fisika saling cek — anomali > 3σ residual → peringatan.

---

## 6. Capability detection

Fitur menyala/mati **otomatis** dari data — inti prinsip P3 (`capability.py`).

```mermaid
flowchart TD
    START(["df kanonik"]) --> LOOP{"untuk tiap kolom:<br/>nunique ≥ 5 ?"}
    LOOP -->|"bervariasi"| ON["fitur ON<br/>model belajar kolom itu"]
    LOOP -->|"konstan (nunique&lt;5)"| OFFf["fitur OFF<br/>+ fallback fisika"]

    ON --> EX1["✅ al_feed_t, digester_temp_c,<br/>naoh_conc_gl … (711–997 unik)"]
    OFFf --> EX2["⛔ predesil_eff, ca_si_ratio,<br/>clarif_eff, causticity, na2co3_conv_eff<br/>(1 nilai — standar industri)"]

    EX2 -.->|"jika data tahap-2<br/>memvariasikan → otomatis ON"| ON
```

Kolom konstan = **standar industri Bayer** (Ca/Si 1.2, causticity 0.85, dst),
divalidasi jalur fisika. Bukan bug — desain jujur: fitur baru menyala sendiri
begitu data mendukung. Detail: [14-batasan.md](14-batasan.md).

---

## 7. Sequence advisory

Satu siklus dari "operator buka jam-N" sampai kartu muncul (jalur Next.js).

```mermaid
sequenceDiagram
    autonumber
    participant U as Operator
    participant FE as Next.js
    participant API as REST API
    participant CT as contract.py
    participant ML as predict.py
    participant PH as physics/
    participant AD as advisory/

    U->>FE: pilih jam / skenario
    FE->>API: GET /v1/replay/{s}/hour/{h}
    API->>CT: call("replay_hour", …)
    CT->>ML: prediksi target
    CT->>PH: neraca massa + Na + karbonasi
    CT->>AD: context (angka+SHAP+alarm) → Kartu
    AD-->>CT: kartu advisory (grounded)
    CT-->>API: kpi + cards + neraca
    API-->>FE: JSON
    FE-->>U: KPI + Kartu (Terima/Tolak/Peta)
    U->>FE: Terima / Tolak
    FE->>FE: catat ke audit trail + toast
```

Jika `LLM_PROVIDER` diset (ollama/groq/gemini), langkah `context → Kartu`
memakai LLM untuk **membahasakan** angka; gagal apa pun → jatuh ke template
deterministik (P6). Default: template, offline, tanpa token.

---

## 8. Roadmap integrasi

Tier integrasi produksi (doc 07). Yang tebal = **sudah ada**; putus-putus =
roadmap.

```mermaid
flowchart LR
    subgraph NOW["Sekarang (nyata)"]
      REST["Tier 1 · REST API<br/>FastAPI + OpenAPI /docs"]
    end
    subgraph NEXT["Roadmap"]
      MQTT["Tier 2 · Event MQTT<br/>push alarm/advisory"]
      MCP["Tier 3 · MCP server<br/>tools utk agen AI"]
      OPC["OPC UA / Historian<br/>telemetri read-only"]
      AUTH["AuthN/Z produksi<br/>SSO korporat + RBAC"]
    end

    CORE["Inti headless (contract.py)"] --> REST
    CORE -.-> MQTT
    CORE -.-> MCP
    OPC -.->|adapter| CORE
    AUTH -.->|gerbang| REST

    classDef now fill:#199e7022,stroke:#199e70,color:#111;
    class REST now;
```

Ketiga tier berbagi **definisi endpoint yang sama** (`contract.py`) — menambah
MQTT/MCP = iterasi daftar yang sudah ada, bukan tulis ulang. Auth: lihat catatan
di [07-integrasi-produksi.md](07-integrasi-produksi.md) (produksi: SSO + RBAC per
peran CRO/Supervisor/Admin).

---

### Cara render diagram

- **GitHub / GitLab** — otomatis (blok ```mermaid```).
- **VS Code** — ekstensi *Markdown Preview Mermaid Support*, lalu `Ctrl+Shift+V`.
- **Ekspor gambar** — [mermaid.live](https://mermaid.live) (tempel kode blok) →
  unduh SVG/PNG untuk slide presentasi.
