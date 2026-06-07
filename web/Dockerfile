FROM node:20-bookworm-slim

WORKDIR /app

COPY web/package.json web/package-lock.json ./
RUN npm ci

COPY web ./
RUN npm run build

EXPOSE 3003

CMD ["npm", "run", "start", "--", "--hostname", "0.0.0.0", "--port", "3003"]
