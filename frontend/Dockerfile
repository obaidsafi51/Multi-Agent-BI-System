# Optimized Next.js Dockerfile - Single stage for development, faster builds
FROM node:22-alpine

WORKDIR /app

# Install system dependencies and create user early (curl for health checks)
RUN apk update && apk add --no-cache curl && \
    npm config set registry https://registry.npmjs.org/ && \
    npm config set fetch-timeout 300000 && \
    addgroup -g 1001 -S nodejs && \
    adduser -S nextjs -u 1001

# Copy package files first for better Docker layer caching
COPY package*.json ./

# Install dependencies with npm cache optimization (use install instead of ci for development)
RUN npm install --prefer-offline --no-audit --progress=false && \
    npm cache clean --force


# Copy source code (excluding node_modules, .next via .dockerignore)
COPY . .

# Set ownership and create necessary directories with proper permissions
RUN chown -R nextjs:nodejs /app && \
    mkdir -p /app/.next && \
    chmod 755 /app/.next && \
    chown -R nextjs:nodejs /app/.next

# Switch to non-root user
USER nextjs

# Create .next directory with proper permissions as nextjs user
RUN mkdir -p /app/.next && chmod 755 /app/.next

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000 || exit 1

# Start development server (docker-compose specifies dev:stable to avoid Turbopack issues)
CMD ["npm", "run", "dev:stable"]