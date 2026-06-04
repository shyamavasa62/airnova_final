## AIRNOVA Quick Start

Run the app (backend + frontend) with one command:

```bash
./run_airnova.sh start
```

Then open:

- `http://127.0.0.1:8080/index.html`

Useful commands:

```bash
./run_airnova.sh status
./run_airnova.sh stop
```

Run tests:

```bash
python3 -m pip install -r requirements.txt
pytest
```

Notes:
- Backend default port: `5000`
- Frontend default port: `8080`
- You can override ports: `BACKEND_PORT=5001 FRONTEND_PORT=8081 ./run_airnova.sh start`
