import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true, // Re-enabled with proper WebSocket protection
  
  // Remove proxy rewrites - let frontend make direct API calls
  // This avoids the "socket hang up" and "ECONNRESET" errors
  // Frontend will use NEXT_PUBLIC_API_URL from environment variables
};

export default nextConfig;
