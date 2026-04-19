FROM node:22-slim

WORKDIR /app

# Deps layer — cached unless package*.json change. Seeds the node_modules volume
# on first boot; the CMD below keeps it in sync with package.json on every start.
COPY package.json package-lock.json ./
RUN npm ci

# Source is bind-mounted in compose; this COPY keeps the image standalone.
COPY . .

EXPOSE 5173
# `npm install` is a fast no-op when node_modules already matches the lockfile,
# and a resync when the host's package.json/lock has new deps. This means adding
# a dep on the host + restarting the container is enough — no rebuild needed.
CMD ["sh", "-c", "npm install --no-audit --no-fund && npm run dev -- --host 0.0.0.0"]
