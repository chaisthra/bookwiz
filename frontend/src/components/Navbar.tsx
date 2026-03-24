"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 30);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <nav
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-500 ${
        scrolled
          ? "bg-nf-bg/95 backdrop-blur-sm shadow-lg"
          : "bg-gradient-to-b from-black/80 via-black/30 to-transparent"
      }`}
    >
      <div className="flex items-center justify-between px-8 md:px-14 py-4">
        {/* Logo */}
        <Link
          href="/"
          className="font-serif text-2xl font-bold text-aged-gold tracking-tight hover:opacity-90 transition-opacity"
        >
          BookWiz
        </Link>

        {/* Nav links — desktop */}
        <div className="hidden md:flex items-center gap-7">
          <Link href="/" className="text-sm text-white/75 hover:text-white transition-colors">
            Home
          </Link>
          <Link href="/" className="text-sm text-white/75 hover:text-white transition-colors">
            My Books
          </Link>
          <Link href="/" className="text-sm text-white/75 hover:text-white transition-colors">
            Discover
          </Link>
        </div>

        {/* Right icons */}
        <div className="flex items-center gap-5">
          {/* Search icon */}
          <button className="text-white/60 hover:text-white transition-colors" aria-label="Search">
            <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <circle cx="11" cy="11" r="8" />
              <path d="m21 21-4.35-4.35" strokeLinecap="round" />
            </svg>
          </button>

          {/* Bell icon */}
          <button className="text-white/60 hover:text-white transition-colors" aria-label="Notifications">
            <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6 6 0 00-9.33-4.993M9 17H4l1.405-1.405A2.032 2.032 0 006 14.158V11a6 6 0 016-6M13 21a2 2 0 01-4 0" />
            </svg>
          </button>

          {/* Profile avatar */}
          <div className="h-8 w-8 rounded-md bg-aged-gold/20 border border-aged-gold/40 flex items-center justify-center cursor-pointer hover:border-aged-gold/70 transition-colors">
            <span className="text-xs font-bold text-aged-gold">C</span>
          </div>
        </div>
      </div>
    </nav>
  );
}
