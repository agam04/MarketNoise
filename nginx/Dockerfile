# ── Stage 1: build the React/Vite frontend ───────────────────────────────────
FROM node:20-alpine AS frontend-build

WORKDIR /frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ .

# No VITE_ vars needed — all API calls use relative /api/... paths
RUN npm run build

# ── Stage 2: nginx serves the built SPA ──────────────────────────────────────
FROM nginx:alpine

# Replace default nginx config
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf

# Copy built frontend
COPY --from=frontend-build /frontend/dist /usr/share/nginx/html

# Django static files volume is mounted at /app/staticfiles at runtime
# (see docker-compose.yml — staticfiles volume)

EXPOSE 80
