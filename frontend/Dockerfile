# Build stage
FROM node:22-alpine AS builder

WORKDIR /app

# Install curl for health checks
RUN apk update && apk add --no-cache curl

# Copy package files first for better layer caching
COPY package*.json ./

# Install dependencies
RUN npm config set registry https://registry.npmmirror.com/ && \
    npm ci --only=production

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Production stage
FROM node:22-alpine AS production

WORKDIR /app

# Install curl for health checks
RUN apk update && apk add --no-cache curl

# Copy package files
COPY package*.json ./

# Install only production dependencies
RUN npm config set registry https://registry.npmmirror.com/ && \
    npm ci --only=production && npm cache clean --force

# Copy built application from builder stage
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public

# Create non-root user
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nextjs -u 1001

# Change ownership of the app directory
RUN chown -R nextjs:nodejs /app
USER nextjs

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000 || exit 1

# Start production server
CMD ["npm", "start"]

# Development stage (for development builds)
FROM node:22-alpine AS development

WORKDIR /app

# Install curl for health checks
RUN apk update && apk add --no-cache curl

# Copy package files
COPY package*.json ./

# Install all dependencies (including devDependencies for development)
RUN npm config set registry https://registry.npmmirror.com/ \
    && npm config set fetch-timeout 600000 \
    && npm config set fetch-retry-mintimeout 20000 \
    && npm config set fetch-retry-maxtimeout 120000 \
    && npm install --prefer-offline --no-audit --progress=false

# Copy source code
COPY . .

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000 || exit 1

# Start development server
CMD ["npm", "run", "dev"]