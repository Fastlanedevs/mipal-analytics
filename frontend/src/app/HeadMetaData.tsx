import Head from "next/head";
import React from "react";

const HeadMetaData = () => {
  const baseUrl = process.env.NEXT_PUBLIC_APP_URL || "";

  return (
    <Head>
      <title>MI PAL - Your AI-powered assistant</title>
      <meta
        name="description"
        content="MI PAL integrates with your enterprise DNA through secure, on-premise AI assistance, transforming knowledge silos into collective intelligence that powers competitive edge and business excellence."
      />
      <meta name="keywords" content="keyword1, keyword2, keyword3" />
      <meta
        name="viewport"
        content="width=device-width, initial-scale=1, viewport-fit=cover"
      />
      <meta name="robots" content="index, follow" />

      {/* Open Graph Tags */}
      <meta property="og:title" content="MI PAL - Your AI-powered assistant" />
      <meta
        property="og:description"
        content="MI PAL integrates with your enterprise DNA through secure, on-premise AI assistance, transforming knowledge silos into collective intelligence that powers competitive edge and business excellence."
      />
      <meta property="og:image" content={`${baseUrl}/favicon.png`} />
      <meta property="og:url" content={baseUrl} />

      {/* Twitter Card Tags */}
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:title" content="MI PAL - Your AI-powered assistant" />
      <meta
        name="twitter:description"
        content="MI PAL integrates with your enterprise DNA through secure, on-premise AI assistance, transforming knowledge silos into collective intelligence that powers competitive edge and business excellence."
      />
      <meta name="twitter:image" content={`${baseUrl}/favicon.png`} />

      <link rel="canonical" href={baseUrl} />
      <link rel="icon" href={`${baseUrl}/favicon.png`} />
    </Head>
  );
};

export default HeadMetaData;
