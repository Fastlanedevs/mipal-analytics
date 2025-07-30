const createNextIntlPlugin = require("next-intl/plugin");

const withNextIntl = createNextIntlPlugin();

/** @type {import('next').NextConfig} */
const nextConfig = {
  env: {
    NEXTAUTH_URL: process.env.NEXTAUTH_URL,
    NEXTAUTH_SECRET: process.env.NEXTAUTH_SECRET,
    NEXT_PUBLIC_BACKEND_URL: process.env.NEXT_PUBLIC_BACKEND_URL,
    NEXT_PUBLIC_APP_URL: process.env.NEXT_PUBLIC_APP_URL,
  },
  webpack: (config, { isServer }) => {
    // Ignore OpenTelemetry warnings
    config.ignoreWarnings = [
      { module: /@opentelemetry/ },
      { module: /instrumentation/ },
    ];

    return config;
  },
  async redirects() {
    return [];
  },
  async rewrites() {
    return [];
  },
  // Ensure ngrok URLs are allowed if needed
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [{ key: "Access-Control-Allow-Origin", value: "*" }],
      },
    ];
  },
};

module.exports = withNextIntl(nextConfig);
