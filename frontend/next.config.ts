import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The blog MDX files live in ../content/blog (repo root), one level above
  // the frontend. Allow the server to read them at build time.
  serverExternalPackages: ["gray-matter", "reading-time"],
  turbopack: {
    root: __dirname,
  },
};

export default nextConfig;
