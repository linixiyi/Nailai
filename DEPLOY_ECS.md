# NailAI ECS Deployment

This project runs as two Docker services:

- `web`: Next.js frontend on `127.0.0.1:3003`
- `ai-service`: FastAPI backend on the internal Docker network

Nginx exposes the frontend publicly on port `80`. The Next.js runtime proxy forwards `/api/v1/*` requests to FastAPI.

## First Deployment

```bash
git clone -b feature/new-approach git@github.com:linixiyi/MeiTuanHackathon.git
cd MeiTuanHackathon
docker compose up -d --build
sudo cp deploy/nginx/nailai.conf /etc/nginx/conf.d/nailai.conf
sudo nginx -t
sudo systemctl reload nginx
curl -I http://127.0.0.1:3003
curl http://127.0.0.1:8008/health
```

## Update Deployment

```bash
cd ~/MeiTuanHackathon
git pull --rebase origin feature/new-approach
docker compose up -d --build
sudo nginx -t
sudo systemctl reload nginx
```

## Logs

```bash
docker compose ps
docker compose logs --tail=100 web
docker compose logs --tail=100 ai-service
```
