import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Keluaran mandiri: server + hanya node_modules yang benar-benar dipakai,
  // supaya image Docker ramping (lihat frontend/Dockerfile). Tidak mengubah
  // `npm run dev` / `npm start` untuk pemakaian lokal biasa.
  //
  // Dinyalakan HANYA lewat env, bukan selalu: Vercel punya pipeline build
  // sendiri dan tidak memakai keluaran standalone, jadi menyalakannya di sana
  // hanya menambah variabel tak perlu pada jalur deploy yang dipakai juri
  // (lihat docs/22-deploy.md bagian A2). frontend/Dockerfile menyetel env ini
  // sebelum `npm run build`; kalau lupa, COPY .next/standalone di Dockerfile
  // gagal keras saat build — bukan diam-diam menghasilkan image rusak.
  ...(process.env.BUILD_STANDALONE === "1"
    ? { output: "standalone" as const }
    : {}),
};

export default nextConfig;
