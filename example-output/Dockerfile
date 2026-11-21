# Space Fractions — Node.js 18 runtime (Docker 20)
FROM node:18-alpine AS base
WORKDIR /app

COPY package*.json ./
RUN npm install --production=false

COPY . .

# One image, selectable entrypoint per microservice (Game/Question/User).
# Build: docker build -t space-fractions .
# Run:   docker run -e SERVICE=game-component -p 3000:3000 space-fractions
FROM node:18-alpine
WORKDIR /app
COPY --from=base /app ./

ENV NODE_ENV=production
ENV SERVICE=game-component

EXPOSE 3000 3001 3002

CMD ["sh", "-c", "node src/${SERVICE}/server.js"]
