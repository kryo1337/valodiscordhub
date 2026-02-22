FROM oven/bun:1-alpine AS build
WORKDIR /app

ARG VITE_API_BASE_URL=http://localhost:8000
ARG VITE_WS_URL=ws://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_WS_URL=$VITE_WS_URL

COPY package.json bun.lock* ./
RUN bun install --frozen-lockfile

COPY . .
RUN bun run build

FROM oven/bun:1-alpine AS runtime
WORKDIR /app

COPY --from=build /app/dist ./dist
COPY --from=build /app/package.json ./

RUN bun add serve

EXPOSE 5173

CMD ["bun", "run", "serve", "--listen", "5173", "dist"]
