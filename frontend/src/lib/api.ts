import axios from "axios";

const backend = axios.create({ baseURL: "/api/backend" });

export async function getProfiles() {
  const { data } = await backend.get("/profiles");
  return data as Profile[];
}

export async function uploadBook(file: File, profileId: string, mode: "auto" | "manual") {
  const form = new FormData();
  form.append("file", file);
  form.append("profile_id", profileId);
  form.append("mode", mode);
  const { data } = await backend.post("/upload", form);
  return data as { book_id: string; status: string; mode: string };
}

export async function getBooks(profileId: string) {
  const { data } = await backend.get("/books", { params: { profile_id: profileId } });
  return data as Book[];
}

export async function getBook(bookId: string) {
  const { data } = await backend.get(`/books/${bookId}`);
  return data as BookDetail;
}

export async function getVisualStatus(bookId: string) {
  const { data } = await backend.get(`/books/${bookId}/visual-status`);
  return data as VisualStatus;
}

export async function getScrapbook(bookId: string) {
  const { data } = await backend.get(`/books/${bookId}/scrapbook`);
  return data as ScrapbookDetail;
}

export async function generateVisuals(bookId: string) {
  const { data } = await backend.post(`/books/${bookId}/generate-visuals`);
  return data as { status: string };
}

export async function updateScrapbook(
  bookId: string,
  update: { layout?: object; finalised?: boolean }
) {
  const { data } = await backend.patch(`/books/${bookId}/scrapbook`, update);
  return data;
}

export async function getNextScenes(bookId: string, offset = 0) {
  const { data } = await backend.get(`/books/${bookId}/scenes/next`, { params: { offset } });
  return data as { scenes: Scene[]; offset: number };
}

export async function selectScenes(
  bookId: string,
  approvedIds: string[],
  rejectedIds: string[],
  freeText?: string
) {
  const { data } = await backend.post(`/books/${bookId}/scenes/select`, {
    approved_ids: approvedIds,
    rejected_ids: rejectedIds,
    free_text: freeText ?? null,
  });
  return data;
}

// ── Types ──────────────────────────────────────────────────────────────────────

export interface Profile {
  id: string;
  profile_name: string;
  avatar_url: string | null;
  backdrop_style: Record<string, string>;
  preferred_genres: string[];
  is_default: boolean;
}

export interface Book {
  id: string;
  title: string;
  author: string | null;
  genre: string | null;
  status: string;
  visual_status: string | null;
  current_step: string | null;
  created_at: string;
}

export interface Character {
  id: string;
  name: string;
  is_real_person: boolean;
  attributes: Record<string, string>;
  portrait_url: string | null;
  inferred_traits: {
    personality: string[];
    emotional_archetype: string;
    role: string;
    key_quote: string;
  };
}

export interface Scene {
  id: string;
  title: string;
  mood: string;
  emotional_context: string;
  characters_present: string[];
  quote: string;
  context_snippet: string;
  emotional_weight_score: number;
  user_approved: boolean | null;
  image_url: string | null;
}

export interface BookDetail {
  book: Book;
  characters: Character[];
  scenes: Scene[];
}

export interface VisualStatus {
  visual_status: string | null;
  current_step: string | null;
}

export interface AestheticBrief {
  overall_vibe: string;
  color_palette: {
    primary: string;
    secondary: string;
    accent: string;
    background: string;
    text: string;
  };
  typography_mood: string;
  layout_style: string;
  texture: string;
  lighting_mood: string;
  image_filter: string;
  quote_card_style: string;
  moodboard_composition: string;
}

export interface ScrapbookRecord {
  id: string;
  book_id: string;
  aesthetic_brief: AestheticBrief;
  layout: Record<string, unknown>;
  finalised: boolean;
}

export interface ScrapbookDetail {
  scrapbook: ScrapbookRecord;
  characters: Character[];
  scenes: Scene[];
}
