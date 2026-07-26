// Identitas halaman — dipakai rail navigasi, Shell, DAN sinkronisasi URL.
// Ditaruh di lib/ (bukan components/Rail.tsx) supaya store bisa memakainya
// tanpa mengimpor komponen — menghindari impor melingkar lib -> components.

export const PAGE_IDS = [
  "overview", "diagram", "digesti", "liquor", "presipitasi",
  "redmud", "lab", "knowledge", "integrasi",
] as const;

export type PageId = (typeof PAGE_IDS)[number];

export function isPageId(v: string | null | undefined): v is PageId {
  return !!v && (PAGE_IDS as readonly string[]).includes(v);
}
