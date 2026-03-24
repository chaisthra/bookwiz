"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Image from "next/image";
import {
  getScrapbook,
  getBook,
  generateVisuals,
  updateScrapbook,
  ScrapbookDetail,
  Book,
  AestheticBrief,
} from "@/lib/api";
import CharacterCard from "@/components/CharacterCard";
import SceneCard from "@/components/SceneCard";

// ── Layout variants ───────────────────────────────────────────────────────────

function SceneGrid({ scenes, layoutStyle }: { scenes: ScrapbookDetail["scenes"]; layoutStyle: string }) {
  if (layoutStyle === "film-strip") {
    return (
      <div className="flex gap-4 overflow-x-auto no-scrollbar pb-2">
        {scenes.map((s) => <SceneCard key={s.id} scene={s} large />)}
      </div>
    );
  }

  if (layoutStyle === "centered-minimal") {
    return (
      <div className="max-w-2xl mx-auto space-y-10">
        {scenes.map((s) => <SceneCard key={s.id} scene={s} large />)}
      </div>
    );
  }

  // Default: editorial-grid / collage-layered / polaroid-scatter
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
      {scenes.map((s, i) => (
        <div
          key={s.id}
          className={`
            ${layoutStyle === "collage-layered" && i === 0 ? "md:col-span-2" : ""}
            ${layoutStyle === "polaroid-scatter" ? `rotate-[${(i % 3) - 1}deg]` : ""}
          `}
        >
          {/* Scene full-bleed card for grid view */}
          <div className="group relative rounded-xl overflow-hidden border border-white/8 bg-nf-card hover:border-white/20 transition-all hover:scale-[1.01] hover:shadow-2xl">
            {s.image_url ? (
              <div className="relative h-48 w-full">
                <Image
                  src={s.image_url}
                  alt={s.title}
                  fill
                  className="object-cover transition-transform duration-500 group-hover:scale-105"
                  sizes="(max-width: 768px) 100vw, (max-width: 1280px) 50vw, 33vw"
                />
                <div
                  className="absolute inset-0"
                  style={{ background: "linear-gradient(to bottom, transparent 40%, rgba(20,20,20,0.95) 100%)" }}
                />
                <div className="absolute bottom-0 left-0 right-0 p-4">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-white/50 mb-1 block">
                    {s.mood}
                  </span>
                  <h3 className="font-serif text-base font-bold text-white leading-tight">{s.title}</h3>
                </div>
              </div>
            ) : (
              <div className="h-48 bg-nf-surface flex items-center justify-center">
                <span className="text-white/20 text-sm">No image</span>
              </div>
            )}
            <div className="p-4">
              <p className="text-xs text-white/60 leading-relaxed line-clamp-2 mb-3">
                {s.emotional_context}
              </p>
              {s.quote && (
                <blockquote className="border-l-2 border-aged-gold/40 pl-3 font-serif text-xs italic text-white/60 line-clamp-3">
                  &ldquo;{s.quote.length > 160 ? s.quote.slice(0, 160) + "…" : s.quote}&rdquo;
                </blockquote>
              )}
              {s.characters_present?.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-3">
                  {s.characters_present.map((c) => (
                    <span key={c} className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] text-white/50">
                      {c}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Color swatch ──────────────────────────────────────────────────────────────

function ColorPalette({ palette }: { palette: AestheticBrief["color_palette"] }) {
  return (
    <div className="flex items-center gap-2 flex-wrap">
      {Object.entries(palette).map(([name, hex]) => (
        <div key={name} className="flex flex-col items-center gap-1">
          <div
            className="h-8 w-8 rounded-full border border-white/20 shadow-md"
            style={{ background: hex }}
            title={`${name}: ${hex}`}
          />
          <span className="text-[9px] text-white/30 capitalize">{name}</span>
        </div>
      ))}
    </div>
  );
}

// ── Tag pill ──────────────────────────────────────────────────────────────────

function Tag({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[10px] uppercase tracking-wider text-white/30">{label}</span>
      <span className="text-xs text-white/70 capitalize">{value.replace(/-/g, " ")}</span>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function ScrapbookPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const [scrapbook, setScrapbook] = useState<ScrapbookDetail | null>(null);
  const [book, setBook] = useState<Book | null>(null);
  const [loading, setLoading] = useState(true);
  const [polling, setPolling] = useState(false);
  const [briefOpen, setBriefOpen] = useState(false);
  const [finalising, setFinalising] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [noScrapbook, setNoScrapbook] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [bookDetail, sb] = await Promise.all([
        getBook(id),
        getScrapbook(id).catch(() => null),
      ]);
      setBook(bookDetail.book);

      if (sb) {
        setScrapbook(sb);
        setNoScrapbook(false);
        // Stop polling when complete
        const vs = bookDetail.book.visual_status;
        if (!["generating_images", "generating_scrapbook"].includes(vs ?? "")) {
          setPolling(false);
        }
      } else {
        setNoScrapbook(true);
        setPolling(false);
      }
    } catch {
      setPolling(false);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    if (!polling) return;
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [fetchData, polling]);

  const handleGenerateVisuals = async () => {
    setGenerating(true);
    setPolling(true);
    try {
      await generateVisuals(id);
    } finally {
      setGenerating(false);
    }
  };

  const handleFinalise = async () => {
    setFinalising(true);
    try {
      await updateScrapbook(id, { finalised: true });
      setScrapbook((prev) =>
        prev ? { ...prev, scrapbook: { ...prev.scrapbook, finalised: true } } : prev
      );
    } finally {
      setFinalising(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-9 w-9 rounded-full border-2 border-aged-gold border-t-transparent animate-spin" />
      </div>
    );
  }

  const isGenerating = ["generating_images", "generating_scrapbook"].includes(book?.visual_status ?? "");
  const brief = scrapbook?.scrapbook.aesthetic_brief;
  const bgColor = brief?.color_palette?.background ?? "#141414";
  const accentColor = brief?.color_palette?.accent ?? "#c8a84b";
  const layoutStyle = brief?.layout_style ?? "editorial-grid";

  // ── No scrapbook yet ──────────────────────────────────────────────────────
  if (noScrapbook || !scrapbook) {
    return (
      <div className="min-h-screen bg-nf-bg">
        <div className="flex min-h-screen flex-col items-center justify-center gap-6 px-8 text-center">
          <div className="h-16 w-16 rounded-full border border-white/15 bg-white/5 flex items-center justify-center">
            <svg width="28" height="28" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} className="text-white/40">
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 10h16M4 14h10" />
            </svg>
          </div>
          <div>
            <h1 className="font-serif text-2xl font-bold text-white mb-2">No scrapbook yet</h1>
            <p className="text-white/40 text-sm max-w-sm">
              {isGenerating
                ? (book?.current_step ?? "Generating your scrapbook…")
                : "Generate visuals to create your personalised scrapbook."}
            </p>
          </div>
          {isGenerating ? (
            <div className="flex items-center gap-3">
              <div className="h-5 w-5 rounded-full border-2 border-aged-gold border-t-transparent animate-spin" />
              <span className="text-sm text-white/50">{book?.current_step ?? "Working…"}</span>
            </div>
          ) : (
            <div className="flex gap-3">
              <button
                onClick={handleGenerateVisuals}
                disabled={generating}
                className="flex items-center gap-2 rounded-full bg-aged-gold px-7 py-3 text-sm font-bold text-black hover:bg-aged-gold/90 transition-all disabled:opacity-40"
              >
                {generating && <div className="h-4 w-4 rounded-full border-2 border-black border-t-transparent animate-spin" />}
                Generate Visuals
              </button>
              <button
                onClick={() => router.push(`/books/${id}`)}
                className="rounded-full border border-white/15 px-6 py-3 text-sm text-white/60 hover:text-white transition-colors"
              >
                Back to Book
              </button>
            </div>
          )}
        </div>
      </div>
    );
  }

  const { characters, scenes } = scrapbook;
  const approvedScenes = scenes.filter((s) => s.user_approved === true);
  const displayScenes  = approvedScenes.length > 0 ? approvedScenes : scenes;

  return (
    <div className="min-h-screen" style={{ backgroundColor: bgColor }}>

      {/* ── Aesthetic Hero ──────────────────────────────────────────────── */}
      <section
        className="relative pt-28 pb-16 px-8 md:px-14 overflow-hidden"
        style={{
          background: `linear-gradient(135deg, ${accentColor}22 0%, ${bgColor} 60%)`,
        }}
      >
        {/* Grain texture overlay */}
        <div
          className="absolute inset-0 opacity-[0.03] pointer-events-none"
          style={{
            backgroundImage: "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='1'/%3E%3C/svg%3E\")",
          }}
        />
        <div
          className="absolute bottom-0 left-0 right-0 h-24"
          style={{ background: `linear-gradient(to bottom, transparent, ${bgColor})` }}
        />

        <div className="relative z-10 max-w-3xl animate-fade-up">
          <button
            onClick={() => router.push(`/books/${id}`)}
            className="mb-6 flex items-center gap-1.5 text-xs text-white/40 hover:text-white/80 transition-colors"
          >
            <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
            </svg>
            Back to book
          </button>

          <p className="text-xs font-semibold uppercase tracking-widest mb-2" style={{ color: accentColor }}>
            Scrapbook
          </p>
          <h1 className="font-serif text-3xl md:text-5xl font-bold text-white leading-tight mb-2 text-balance">
            {book?.title ?? "Your Book"}
          </h1>
          {brief?.overall_vibe && (
            <p className="text-lg italic text-white/50 mt-1">{brief.overall_vibe}</p>
          )}

          {isGenerating && (
            <div className="flex items-center gap-3 mt-6">
              <div className="h-5 w-5 rounded-full border-2 border-t-transparent animate-spin" style={{ borderColor: accentColor, borderTopColor: "transparent" }} />
              <span className="text-sm text-white/50">{book?.current_step ?? "Generating visuals…"}</span>
            </div>
          )}

          {scrapbook.scrapbook.finalised && (
            <span className="mt-4 inline-block rounded-full border border-muted-sage/40 bg-muted-sage/10 px-3 py-1 text-xs text-muted-sage">
              Finalised
            </span>
          )}
        </div>
      </section>

      <div className="px-8 md:px-14 pb-24 space-y-16">

        {/* ── Characters ──────────────────────────────────────────────── */}
        {characters.length > 0 && (
          <section className="animate-fade-up">
            <h2 className="mb-6 font-serif text-xl font-semibold text-white">Characters</h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
              {characters.map((c) => (
                <CharacterCard key={c.id} character={c} large />
              ))}
            </div>
          </section>
        )}

        {/* ── Scenes ──────────────────────────────────────────────────── */}
        {displayScenes.length > 0 && (
          <section className="animate-fade-up">
            <h2 className="mb-6 font-serif text-xl font-semibold text-white">
              {approvedScenes.length > 0 ? "Your Scenes" : "Scenes"}
            </h2>
            <SceneGrid scenes={displayScenes} layoutStyle={layoutStyle} />
          </section>
        )}

        {/* ── Aesthetic Brief ──────────────────────────────────────────── */}
        {brief && (
          <section className="animate-fade-up max-w-2xl">
            <button
              onClick={() => setBriefOpen((v) => !v)}
              className="flex items-center gap-2 text-sm text-white/40 hover:text-white/70 transition-colors mb-4"
            >
              <svg
                width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
                className={`transition-transform ${briefOpen ? "rotate-180" : ""}`}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
              </svg>
              {briefOpen ? "Hide" : "Aesthetic Brief"}
            </button>

            {briefOpen && (
              <div className="rounded-2xl border border-white/8 bg-nf-surface p-6 space-y-5">
                <div>
                  <p className="text-[10px] uppercase tracking-wider text-white/30 mb-3">Color Palette</p>
                  <ColorPalette palette={brief.color_palette} />
                </div>

                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <Tag label="Typography" value={brief.typography_mood} />
                  <Tag label="Layout" value={brief.layout_style} />
                  <Tag label="Texture" value={brief.texture} />
                  <Tag label="Lighting" value={brief.lighting_mood} />
                  <Tag label="Image Filter" value={brief.image_filter} />
                </div>

                <div>
                  <p className="text-[10px] uppercase tracking-wider text-white/30 mb-1">Quote Card Style</p>
                  <p className="text-xs text-white/60">{brief.quote_card_style}</p>
                </div>

                <div>
                  <p className="text-[10px] uppercase tracking-wider text-white/30 mb-1">Composition</p>
                  <p className="text-xs text-white/60">{brief.moodboard_composition}</p>
                </div>

                {!scrapbook.scrapbook.finalised && (
                  <button
                    onClick={handleFinalise}
                    disabled={finalising}
                    className="rounded-full border border-muted-sage/40 bg-muted-sage/10 px-5 py-2 text-sm text-muted-sage hover:bg-muted-sage/20 transition-all disabled:opacity-40"
                  >
                    {finalising ? "Finalising…" : "Finalise Scrapbook"}
                  </button>
                )}
              </div>
            )}
          </section>
        )}
      </div>
    </div>
  );
}
