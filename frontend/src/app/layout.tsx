import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/Navbar";

export const metadata: Metadata = {
  title: "BookWiz — Your Book Scrapbook",
  description: "Transform any book into a beautiful digital scrapbook",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen bg-nf-bg text-white antialiased">
        <Navbar />
        {children}
      </body>
    </html>
  );
}
