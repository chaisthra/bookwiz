"use client";

import Image from "next/image";
import { Character } from "@/lib/api";

const ROLE_GRADIENT: Record<string, string> = {
  protagonist:   "from-amber-900/60 to-nf-card",
  antagonist:    "from-red-900/60 to-nf-card",
  love_interest: "from-rose-900/60 to-nf-card",
  mentor:        "from-emerald-900/50 to-nf-card",
  supporting:    "from-slate-700/50 to-nf-card",
  subject:       "from-amber-800/50 to-nf-card",
  author:        "from-blue-900/50 to-nf-card",
  other:         "from-slate-700/50 to-nf-card",
};

const ROLE_ACCENT: Record<string, string> = {
  protagonist:   "text-aged-gold border-aged-gold/30",
  antagonist:    "text-red-400 border-red-400/30",
  love_interest: "text-dusty-rose border-dusty-rose/30",
  mentor:        "text-muted-sage border-muted-sage/30",
  supporting:    "text-white/50 border-white/15",
  subject:       "text-aged-gold border-aged-gold/30",
  author:        "text-blue-300 border-blue-300/30",
  other:         "text-white/50 border-white/15",
};

interface CharacterCardProps {
  character: Character;
  /** Show larger portrait-oriented layout (used on scrapbook page) */
  large?: boolean;
}

export default function CharacterCard({ character, large = false }: CharacterCardProps) {
  const role      = character.inferred_traits?.role ?? "other";
  const gradient  = ROLE_GRADIENT[role] ?? ROLE_GRADIENT.other;
  const accent    = ROLE_ACCENT[role] ?? ROLE_ACCENT.other;
  const traits    = (character.inferred_traits?.personality ?? []).slice(0, 4);
  const archetype = character.inferred_traits?.emotional_archetype ?? "";
  const quote     = character.inferred_traits?.key_quote ?? "";
  const attrs     = character.attributes ?? {};
  const initial   = character.name?.[0]?.toUpperCase() ?? "?";

  const avatarHeight = large ? "h-56" : "h-28";
  const cardWidth    = large ? "w-64" : "w-52";

  return (
    <div
      className={`group relative flex-shrink-0 ${cardWidth} rounded-xl overflow-hidden border border-white/8 bg-gradient-to-b ${gradient} hover:border-white/20 transition-all duration-300 hover:scale-[1.02] hover:shadow-2xl`}
    >
      {/* Avatar / portrait area */}
      <div className={`relative ${avatarHeight} overflow-hidden`}>
        {character.portrait_url ? (
          <Image
            src={character.portrait_url}
            alt={character.name}
            fill
            className="object-cover object-top transition-transform duration-500 group-hover:scale-105"
            sizes={large ? "256px" : "208px"}
          />
        ) : (
          <div className="flex h-full items-center justify-center">
            <div className="h-16 w-16 rounded-full bg-white/10 border border-white/20 flex items-center justify-center">
              <span className="font-serif text-2xl font-bold text-white/80">{initial}</span>
            </div>
            <div
              className="absolute inset-0 opacity-30 blur-2xl"
              style={{ background: "radial-gradient(circle at center, rgba(200,168,75,0.4), transparent 70%)" }}
            />
          </div>
        )}
        {/* Bottom fade into card */}
        <div
          className="absolute bottom-0 left-0 right-0 h-10"
          style={{ background: "linear-gradient(to bottom, transparent, rgba(20,20,20,0.8))" }}
        />
      </div>

      {/* Info */}
      <div className="px-4 pb-4 pt-2">
        <div className="flex items-start justify-between gap-2 mb-2">
          <h3 className="font-serif text-base font-semibold text-white leading-tight">
            {character.name}
          </h3>
          <span className={`flex-shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-medium capitalize ${accent}`}>
            {role.replace("_", " ")}
          </span>
        </div>

        {archetype && (
          <p className="text-xs italic text-white/50 mb-3 line-clamp-2 leading-relaxed">
            {archetype}
          </p>
        )}

        {(attrs.hair || attrs.eyes) && (
          <div className="flex gap-3 text-[11px] text-white/40 mb-3">
            {attrs.hair && <span>Hair: {attrs.hair}</span>}
            {attrs.eyes && <span>Eyes: {attrs.eyes}</span>}
          </div>
        )}

        {traits.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-3">
            {traits.map((t) => (
              <span
                key={t}
                className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] text-white/60"
              >
                {t}
              </span>
            ))}
          </div>
        )}

        {quote && (
          <blockquote className="border-l-2 border-aged-gold/40 pl-2 text-[11px] italic text-white/40 line-clamp-2">
            {quote.length > 100 ? quote.slice(0, 100) + "…" : quote}
          </blockquote>
        )}
      </div>
    </div>
  );
}
