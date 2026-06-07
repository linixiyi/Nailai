# NailAI AI Service

FastAPI service for the P0 try-on pipeline.

Use Python 3.11 for local development:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --reload --port 8008
```

Frontend dev/proxy config expects this service at `http://127.0.0.1:8008` from the server process, with the web app on `http://localhost:3003`.

Optional vision dependencies are isolated so the service can start quickly during early MVP work:

```bash
pip install -r requirements-vision.txt
```
