"""Static boilerplate for a freshly scaffolded Vite + React + TS + Tailwind app."""

PACKAGE_JSON = """{{
  "name": "{app_name}",
  "private": true,
  "version": "0.0.1",
  "type": "module",
  "scripts": {{
    "dev": "vite --port {port} --strictPort",
    "build": "tsc && vite build",
    "lint": "tsc --noEmit"
  }},
  "dependencies": {{
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "lucide-react": "^0.445.0"
  }},
  "devDependencies": {{
    "@types/react": "^18.3.5",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "autoprefixer": "^10.4.20",
    "postcss": "^8.4.47",
    "tailwindcss": "^3.4.10",
    "typescript": "^5.5.4",
    "vite": "^5.4.6"
  }}
}}
"""

VITE_CONFIG = """import {{ defineConfig }} from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({{
  plugins: [react()],
  server: {{ port: {port}, strictPort: true }},
}})
"""

TSCONFIG = """{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true
  },
  "include": ["src"]
}
"""

INDEX_HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{app_name}</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
"""

TAILWIND_CONFIG = """/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: { extend: {} },
  plugins: [],
}
"""

POSTCSS_CONFIG = """export default {
  plugins: { tailwindcss: {}, autoprefixer: {} },
}
"""

MAIN_TSX = """import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
"""

INDEX_CSS = """@tailwind base;
@tailwind components;
@tailwind utilities;
"""

DEFAULT_APP_TSX = """export default function App() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 text-slate-50">
      <div className="text-center space-y-2">
        <h1 className="text-2xl font-semibold">New CyberFactory App</h1>
        <p className="text-slate-400">Describe what to build in the prompter panel.</p>
      </div>
    </div>
  )
}
"""


def render_boilerplate(app_name: str, port: int) -> dict[str, str]:
    return {
        "package.json": PACKAGE_JSON.format(app_name=app_name, port=port),
        "vite.config.ts": VITE_CONFIG.format(port=port),
        "tsconfig.json": TSCONFIG,
        "index.html": INDEX_HTML.format(app_name=app_name),
        "tailwind.config.js": TAILWIND_CONFIG,
        "postcss.config.js": POSTCSS_CONFIG,
        "src/main.tsx": MAIN_TSX,
        "src/index.css": INDEX_CSS,
        "src/App.tsx": DEFAULT_APP_TSX,
    }
