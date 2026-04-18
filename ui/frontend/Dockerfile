FROM node:22-slim

WORKDIR /app

# Deps layer — cached unless package*.json change.
COPY package.json package-lock.json ./
RUN npm ci

# Source is bind-mounted in compose; this COPY keeps the image standalone.
COPY . .

EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
