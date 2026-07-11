# 07 — Integrasi ke Sistem Pabrik (Referensi Masa Depan)

> Ringkasan panjang ada di doc 06 Bagian 8–9. Dokumen ini = catatan teknis integrasi
> yang bisa dibuka lagi saat pitch/juri bertanya, atau saat proyek lanjut pasca-hackathon.

## Arsitektur integrasi target

```
DCS pabrik (Yokogawa / Honeywell / ABB)          [Purdue Level 1–2]
   │  OPC UA (akun READ-ONLY)
   ▼
Plant Historian (OSIsoft PI / AVEVA / TimescaleDB)  [Level 3]
   │  connector + validasi kualitas data (range check, stale check)
   ▼
AI RED MUD engine  ← LAPIS 1–3 kita, TIDAK berubah   [Level 3.5 / DMZ]
   │  REST API internal + dashboard web
   ▼
CRO console (browser)  +  LIMS (hasil lab = ground truth retraining)
```

Kalimat kunci: **satu-satunya komponen yang diganti dari demo adalah Lapis 0** —
replay dicabut, connector historian dicolok. Lapis model/fisika/optimizer/advisory utuh.

## Roadmap 3 fase

| Fase | Durasi | Isi | Risiko ke pabrik |
|---|---|---|---|
| 1. Shadow mode | 0–3 bln | Baca historian, tampilkan advisory, TIDAK mengendalikan; akurasi dibanding hasil lab | Nol (read-only) |
| 2. Advisory resmi | 3–9 bln | Soft sensor causticity tervalidasi vs LIMS; setpoint dipakai CRO dengan approval supervisor; KPI penghematan diukur | Rendah (human-in-the-loop) |
| 3. Closed-loop / APC | 9+ bln | Setpoint ditulis balik ke DCS dalam amplop aman | Perlu MOC & validasi formal |

## Checklist komponen tambahan untuk produksi (JANGAN dibangun saat hackathon)

- [ ] Connector OPC UA / PI Web API + buffer lokal saat jaringan putus
- [ ] Validasi data masuk: range fisik, sensor freeze/stale, missing → jangan umpan model
- [ ] Uncertainty: quantile LightGBM / conformal prediction (advisory wajib punya error bar)
- [ ] Drift monitoring: residual prediksi vs lab, alarm bila keluar pita
- [ ] Retraining terjadwal + model registry (MLflow) + rollback
- [ ] Fitur lag/rolling dari historian (steady-state → dinamis; dead-time proses nyata)
- [ ] Guardrail hard-constraint dari batas alarm DCS (bukan cuma rentang data training)
- [ ] Audit trail advisory + keputusan operator (terima/tolak + alasan)
- [ ] AuthN/AuthZ: AD/SSO, role CRO / supervisor / engineer
- [ ] LLM: deployment VPC/on-prem atau redaksi data sensitif; fallback template

## Keamanan — poin siap pakai untuk menjawab juri

1. Read-only terhadap pabrik (Fase 1–2) → kompromi aplikasi ≠ kompromi kontrol.
2. Duduk di DMZ (Purdue 3.5), tidak pernah menyentuh Level 1–2 langsung.
3. Human-in-the-loop: sistem tidak pernah mengeksekusi; manusia memutuskan.
4. Semua rekomendasi di-clamp ke amplop operasi aman sebelum tampil.
5. Prompt LLM = JSON dari model sendiri, bukan input bebas → prompt injection minimal.
6. Demo hackathon: data 100% sintetis → tidak ada isu kerahasiaan.

> Satu kalimat slide: *"Read-only, human-in-the-loop, ter-guardrail —
> jalur adopsi paling aman untuk AI di lingkungan OT."*
