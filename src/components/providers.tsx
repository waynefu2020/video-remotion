"use client";

import { ThemeProvider } from "next-themes";
import { Toaster } from "@/components/ui/sonner";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider forcedTheme="light" attribute="class" enableSystem={false}>
      {children}
      <Toaster />
    </ThemeProvider>
  );
}
