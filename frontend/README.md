# Flowspace frontend

React single-page client for the multi-tenant project workflow API. The UI is organized by reusable components, page routes, API access, and auth state:

```text
src/
  api/          Axios client, tenant headers, refresh-token rotation
  components/   Navigation shell, protected routes, feedback, modals
  pages/        Authentication, dashboard, organizations, projects, tasks, members
  state/        Auth and organization context
```

## Run locally

1. Start the FastAPI service on `http://localhost:8000`.
2. From this directory, install packages with `npm install`.
3. Copy `.env.example` to `.env` if the API uses a different URL.
4. Start the Vite development server with `npm run dev`.

In Windows shells, if the workspace path contains an ampersand and npm script execution misparses it, run Vite directly from this directory:

```powershell
node .\node_modules\vite\bin\vite.js
node .\node_modules\vite\bin\vite.js build
```

## Included flows

- Registration and login with protected client routes and rotating refresh tokens.
- Organization switching; every request carries the selected `X-Organization-ID`.
- Role-aware project and member actions, project/task lists, workflow board and task detail.
- Search, status/priority filters, paginated list requests, comments/mentions, notifications, profile and password settings.
- Responsive layout with loading, empty, validation, success, and API error states.

The backend remains the source of truth for authorization, tenant isolation, task workflow transitions, and assignment rules.
