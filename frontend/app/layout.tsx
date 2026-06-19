import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "./context/AuthContext";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: "SparqAI — ROI Decision Intelligence",
    template: "%s | SparqAI",
  },
  description:
    "Multi-touch attribution for every GTM investment. Track ROI on hiring, ad campaigns, tools, and vendors in one dashboard.",
  keywords: [
    "ROI attribution",
    "decision intelligence",
    "GTM analytics",
    "revenue attribution",
    "SaaS analytics",
  ],
  robots: {
    index: false,
    follow: false,
  },
  openGraph: {
    title: "SparqAI — ROI Decision Intelligence",
    description: "Multi-touch attribution for every GTM investment decision.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
