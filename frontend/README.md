# SafeGuard-PQ — frontend

React + TypeScript + three.js (React Three Fiber) GUI built with Vite.

```bash
npm ci
npm run dev            # http://127.0.0.1:5173, proxies /api to SAFEGUARD_API (default http://127.0.0.1:8000)
npm run typecheck && npm run build
npx playwright install chromium && npx playwright test   # starts backend + frontend on ports 8765/5199
```
