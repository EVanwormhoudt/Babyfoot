FROM node:22-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
ARG PUBLIC_API_BASE=""
ENV PUBLIC_API_BASE=${PUBLIC_API_BASE}
RUN npm run build

FROM node:22-alpine

WORKDIR /app
ENV NODE_ENV=production

COPY package.json package-lock.json ./
RUN npm ci --omit=dev
COPY --from=builder /app/build ./build

EXPOSE 3000

CMD ["node", "build"]
