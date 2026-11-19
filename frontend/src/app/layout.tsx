import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TruthLens — Multimodal Digital Forensics & Deepfake Detection",
  description:
    "Enterprise Digital Evidence Authentication and Multimodal Deepfake Verification Suite",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark h-full antialiased">
      <body className="min-h-full bg-[#090d16] text-[#f3f4f6] flex flex-col font-sans">
        {children}
      </body>
    </html>
  );
}
