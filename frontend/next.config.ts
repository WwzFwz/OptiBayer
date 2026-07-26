import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Keluaran mandiri: server + hanya node_modules yang benar-benar dipakai,
  // supaya image Docker ramping (lihat frontend/Dockerfile). Tidak mengubah
  // `npm run dev` / `npm start` untuk pemakaian lokal biasa.
  output: "standalone",
};

export default nextConfig;
