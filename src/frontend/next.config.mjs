/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    optimizePackageImports: ['lucide-react', '@radix-ui/react-icons'],
  },
  async rewrites() {
    return [
      {
        source: '/api/backend/:path*',
        destination: 'http://localhost:8000/:path*', // Backend server
      },
      {
        source: '/ws/:path*',
        destination: 'http://localhost:8000/ws/:path*', // WebSocket proxy
      },
    ];
  },
};

export default nextConfig;