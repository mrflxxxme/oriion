import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./styles/index.css";

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Root element #root not found in index.html");
}

createRoot(rootElement).render(
  <StrictMode>
    <div className="flex min-h-screen items-center justify-center bg-neutral-50 text-neutral-900 dark:bg-neutral-950 dark:text-neutral-100">
      <div className="text-center">
        <h1 className="text-3xl font-semibold tracking-tight">TEAMLY_RU</h1>
        <p className="mt-2 text-sm text-neutral-500">Frontend skeleton ready · Phase 00.1</p>
      </div>
    </div>
  </StrictMode>,
);
