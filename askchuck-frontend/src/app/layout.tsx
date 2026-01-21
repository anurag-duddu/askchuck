import type { Metadata } from "next";
import { EB_Garamond, Crimson_Pro, JetBrains_Mono } from "next/font/google";
import "./globals.css";

// Display font for headings - elegant serif
const garamond = EB_Garamond({
  variable: "--font-display",
  subsets: ["latin"],
  display: "swap",
});

// Body font for reading - refined serif
const crimson = Crimson_Pro({
  variable: "--font-body",
  subsets: ["latin"],
  display: "swap",
});

// Monospace for code - technical precision
const jetbrains = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "AskChuck - Explore Charles Owen's Design Research",
  description: "An AI-powered research assistant for exploring Charles Owen's groundbreaking work in design methodology, design research, and structured planning.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${garamond.variable} ${crimson.variable} ${jetbrains.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
