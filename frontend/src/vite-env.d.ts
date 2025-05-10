/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string
  // Weitere Umgebungsvariablen hier definieren...
}

interface ImportMeta {
  readonly env: ImportMetaEnv
} 