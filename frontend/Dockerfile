FROM node:20-alpine AS deps

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

FROM node:20-alpine AS builder

WORKDIR /app/frontend

ARG NEXT_PUBLIC_BACKEND_URL=http://web:5000
ENV NEXT_TELEMETRY_DISABLED=1 \
    NEXT_PUBLIC_BACKEND_URL=$NEXT_PUBLIC_BACKEND_URL

COPY --from=deps /app/frontend/node_modules ./node_modules
COPY frontend ./

RUN npm run build

FROM node:20-alpine AS runner

WORKDIR /app/frontend

ARG NEXT_PUBLIC_BACKEND_URL=http://web:5000
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    NEXT_PUBLIC_BACKEND_URL=$NEXT_PUBLIC_BACKEND_URL

COPY --from=builder /app/frontend/package.json ./package.json
COPY --from=builder /app/frontend/node_modules ./node_modules
COPY --from=builder /app/frontend/.next ./.next
COPY --from=builder /app/frontend/public ./public
COPY --from=builder /app/frontend/next.config.js ./next.config.js

EXPOSE 3000

CMD ["npm", "run", "start", "--", "-p", "3000"]
