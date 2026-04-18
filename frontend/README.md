# Frontend — ProfeTEC.IA

React 19 + Vite.

## Arranque local

```bash
npm install
cp .env.example .env.local
npm run dev
```

Abrir http://localhost:5173.

Requiere el backend corriendo en `VITE_API_URL` (por defecto http://localhost:8080).

## Build de producción

```bash
npm run build
npm run preview    # sirve el build en 8080
```

## Lint

```bash
npm run lint
```

## Build de imagen Docker

```bash
docker build --build-arg VITE_API_URL=https://tu-backend.run.app -t profetec-frontend .
docker run -p 8080:8080 profetec-frontend
```
