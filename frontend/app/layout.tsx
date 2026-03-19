import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Email LLM Web App",
  description: "Generate and send emails from a web UI backed by OpenAI and FastAPI."
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
