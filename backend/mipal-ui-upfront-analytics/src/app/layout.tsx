import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "../styles/globals.css";
import { Providers } from "./providers";
import "katex/dist/katex.min.css";
import { ThemeProvider } from "next-themes";
import "@/styles/theme.css";
import { NextIntlClientProvider } from "next-intl";
import { getLocale } from "next-intl/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth.config";
import HeadMetaData from "./HeadMetaData";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "MI PAL - Your AI-powered assistant",
  description:
    "MI PAL integrates with your enterprise DNA through secure, on-premise AI assistance, transforming knowledge silos into collective intelligence that powers competitive edge and business excellence.",
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await getServerSession(authOptions);
  const defaultLocale = await getLocale();

  let locale = defaultLocale;
  let messages;

  try {
    if (session) {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_URL}/user/settings`,
        {
          headers: {
            Authorization: `Bearer ${
              session.access_token ?? session.user.access_token
            }`,
          },
        }
      );

      if (response.ok) {
        const userSettings = await response.json();
        locale = userSettings?.language || defaultLocale;
      }
    }
    messages = (await import(`../../messages/${locale}.json`)).default;
  } catch (error) {
    console.error("Error loading messages:", error);
    // Use default locale messages as fallback instead of notFound()
    locale = defaultLocale;
    messages = (await import(`../../messages/${defaultLocale}.json`)).default;
  }

  return (
    <html lang={locale} suppressHydrationWarning key={locale}>
      <HeadMetaData />
      <body className="min-h-screen antialiased bg-white dark:bg-zinc-900">
        <NextIntlClientProvider locale={locale} messages={messages}>
          <ThemeProvider
            attribute="class"
            defaultTheme="system"
            enableSystem
            disableTransitionOnChange
          >
            <Providers>{children}</Providers>
          </ThemeProvider>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
