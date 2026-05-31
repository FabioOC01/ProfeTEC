# Frontend — ProfeTEC.IA

SPA en **React 19 + Vite**, con React Router, Axios y Firebase Auth (Google).

## Arranque local

```bash
npm install
cp .env.example .env.local       # rellenar con la config Web de Firebase
npm run dev
```

Abrir http://localhost:5174 (puerto fijado en [`vite.config.js`](vite.config.js)).

## Configuración (`.env.local`)

Valores tomados de Firebase Console → Configuración del proyecto → Tus apps → Web
(ver [`.env.example`](.env.example)):

| Variable | Descripción |
|---|---|
| `VITE_API_URL` | URL del backend. En local: `http://localhost:8080`. |
| `VITE_FIREBASE_API_KEY` | API key Web de Firebase. |
| `VITE_FIREBASE_AUTH_DOMAIN` | Dominio de autenticación. |
| `VITE_FIREBASE_PROJECT_ID` | ID del proyecto Firebase. |
| `VITE_FIREBASE_APP_ID` | ID de la app Web. |

## Scripts

| Comando | Acción |
|---|---|
| `npm run dev` | Servidor de desarrollo (Vite). |
| `npm run build` | Build de producción a `dist/`. |
| `npm run preview` | Sirve el build de producción localmente. |
| `npm run lint` | ESLint sobre todo el proyecto. |

## Estructura

```
frontend/
├── index.html
├── vite.config.js
├── public/
│   └── logo.png
└── src/
    ├── main.jsx            Entrada + rutas (React Router)
    ├── firebase.js         Inicialización de Firebase
    ├── index.css           Estilos globales y design tokens
    ├── api/                Clientes HTTP (client, cursos, documentos, chat, quizzes)
    ├── context/
    │   └── AuthContext.jsx Estado de sesión (login Google, perfil, rol)
    ├── components/
    │   ├── Navbar.jsx · RequireAuth.jsx
    │   └── ui/             Componentes visuales (TutorBlob, Icon, CitationPopover, …)
    └── pages/
        ├── Login.jsx · Onboarding.jsx · Dashboard.jsx
        ├── cursos/         Lista y detalle de cursos
        ├── chat/           Chat RAG con modos directo/socrático
        └── quizzes/        Lista y resolución de quizzes
```

## Despliegue

Ver la guía de Cloud Run en [`../docs/deploy.md`](../docs/deploy.md).
