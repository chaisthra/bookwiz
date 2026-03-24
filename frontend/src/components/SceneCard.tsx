"use client";

import Image from "next/image";
import { Scene } from "@/lib/api";

const MOOD_CONFIG: Record<string, { border: string; badge: string; glow: string }> = {
  tender:      { border: "border-l-dusty-rose/70",  badge: "bg-dusty-rose/15 text-dusty-rose",  glow: "rgba(201,160,160,0.15)" },
  devastating: { border: "border-l-red-700/70",      badge: "bg-red-900/20 text-red-300",         glow: "rgba(185,28,28,0.15)"  },
  triumphant:  { border: "border-l-aged-gold/70",    badge: "bg-aged-gold/15 text-aged-gold",     glow: "rgba(200,168,75,0.15)" },
  terrifying:  { border: "border-l-red-500/70",      badge: "bg-red-900/25 text-red-400",         glow: "rgba(239,68,68,0.12)"  },
  aching:      { border: "border-l-dusty-rose/50",   badge: "bg-dusty-rose/10 text-white/60",     glow: "rgba(201,160,160,0.10)"},
  electric:    { border: "border-l-aged-gold/90",    badge: "bg-aged-gold/20 text-aged-gold",     glow: "rgba(200,168,75,0.20)" },
  haunting:    { border: "border-l-white/20",        badge: "bg-white/8 text-white/50",           glow: "rgba(255,255,255,0.05)"},
  joyful:      { border: "border-l-muted-sage/70",   badge: "bg-muted-sage/15 text-muted-sage",   glow: "rgba(138,158,138,0.15)"},
  defiant:     { border: "border-l-deep-wine/80",    badge: "bg-deep-wine/25 text-dusty-rose",    glow: "rgba(107,39,55,0.20)"  },
  quiet:       { border: "border-l-white/15",        badge: "bg-white/6 text-white/40",           glow: "rgba(255,255,255,0.03)"},
};

interface SceneCardProps {
  scene: Scene;
  selected?: boolean;
  onToggle?: (id: string) => void;
  selectable?: boolean;
  /** Show larger landscape layout (used on scrapbook page) */
  large?: boolean;
}

export default function SceneCard({
  scene,
  selected = false,
  onToggle,
  selectable = false,
  large = false,
}: SceneCardProps) {
  const cfg   = MOOD_CONFIG[scene.mood?.toLowerCase()] ?? MOOD_CONFIG.quiet;
  const score = scene.emotional_weight_score ?? 0;
  const cardWidth = large ? "w-96" : "w-72";

  return (
    <div
      onClick={() => selectable && onToggle?.(scene.id)}
      className={`
        group relative flex-shrink-0 ${cardWidth} rounded-xl overflow-hidden border-l-4 border border-white/8
        bg-nf-card transition-all duration-300
        ${cfg.border}
        ${selectable ? "cursor-pointer" : ""}
        ${selected
          ? "border-aged-gold/50 bg-aged-gold/8 shadow-lg gold-glow"
          : "hover:border-white/20 hover:bg-nf-elevated hover:shadow-xl hover:scale-[1.02]"}
      `}
      style={selected ? { boxShadow: `0 0 30px ${cfg.glow}` } : undefined}
    >
      {/* Selection ring */}
      {selectable && (
        <div className={`absolute top-3 right-3 z-10 h-5 w-5 rounded-full border-2 transition-all flex items-center justify-center
          ${selected ? "border-aged-gold bg-aged-gold" : "border-white/25 bg-transparent"}`}
        >
          {selected && (
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth={3}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          )}
        </div>
      )}

      {/* Scene image (when available) */}
      {scene.image_url && (
        <div className="relative h-36 w-full overflow-hidden">
          <Image
            src={scene.image_url}
            alt={scene.title}
            fill
            className="object-cover transition-transform duration-500 group-hover:scale-105"
            sizes={large ? "384px" : "288px"}
          />
          <div
            className="absolute bottom-0 left-0 right-0 h-12"
            style={{ background: "linear-gradient(to bottom, transparent, rgba(42,42,42,0.95))" }}
          />
        </div>
      )}

      <div className="p-4 space-y-3">
        {/* Mood + title */}
        <div className="flex items-center gap-2 pr-7 flex-wrap">
          <span className={`rounded-full px-2.5 py-0.5 text-[10px] font-semibold capitalize ${cfg.badge}`}>
            {scene.mood}
          </span>
          <h3 className="font-serif text-sm font-semibold text-white leading-tight">
            {scene.title}
          </h3>
        </div>

        {/* Emotional context */}
        <p className="text-xs text-white/60 leading-relaxed line-clamp-2">
          {scene.emotional_context}
        </p>

        {/* Quote */}
        {scene.quote && (
          <blockquote className="border-l-2 border-aged-gold/40 pl-3 font-serif text-xs italic text-white/70 line-clamp-3 leading-relaxed">
            &ldquo;{scene.quote.length > 140 ? scene.quote.slice(0, 140) + "…" : scene.quote}&rdquo;
          </blockquote>
        )}

        {/* Characters present */}
        {scene.characters_present?.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {scene.characters_present.map((c) => (
              <span key={c} className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] text-white/50">
                {c}
              </span>
            ))}
          </div>
        )}

        {/* Score bar */}
        <div className="h-[2px] w-full overflow-hidden rounded-full bg-white/8">
          <div
            className="h-full rounded-full bg-aged-gold/60 transition-all duration-500"
            style={{ width: `${score * 100}%` }}
          />
        </div>
      </div>
    </div>
  );
}
