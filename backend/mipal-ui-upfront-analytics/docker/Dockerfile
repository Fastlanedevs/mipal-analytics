# Stage 1: Build the application
FROM node:20-alpine AS builder

WORKDIR /app

# Set up npm config first
COPY .npmrc .npmrc
ENV TIPTAP_PRO_TOKEN="gqeOIl68EPa/0TYJy3KzRBlDsAe3Tp6XZHXnPR/JaASe479A9L4DVEs32elxgmnE"

# Copy package files
COPY package*.json ./

# Install dependencies with BuildKit cache mount
RUN --mount=type=cache,target=/root/.npm \
    npm config set @tiptap-pro:registry https://registry.tiptap.dev/ && \
    npm config set //registry.tiptap.dev/:_authToken ${TIPTAP_PRO_TOKEN} && \
    npm ci

# Copy application source code
COPY . .

# Build the application
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# Stage 2: Production image
FROM node:20-alpine

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV TIPTAP_PRO_TOKEN="gqeOIl68EPa/0TYJy3KzRBlDsAe3Tp6XZHXnPR/JaASe479A9L4DVEs32elxgmnE"

# Copy built assets from builder
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/.npmrc ./.npmrc
COPY --from=builder /app/.env .env

# Install production dependencies
RUN npm config set @tiptap-pro:registry https://registry.tiptap.dev/ && \
    npm config set //registry.tiptap.dev/:_authToken ${TIPTAP_PRO_TOKEN} && \
    npm ci --only=production && \
    npm config delete //registry.tiptap.dev/:_authToken && \
    rm -f .npmrc

EXPOSE 3000

CMD ["npm", "start"]
