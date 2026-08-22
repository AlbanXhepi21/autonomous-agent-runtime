import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Local development may be opened through either hostname. This only affects
  // Next's development resource-origin checks; it is not an application API policy.
  allowedDevOrigins: ["localhost", "127.0.0.1"],
};

export default nextConfig;
