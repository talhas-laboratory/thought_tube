import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./app";
import { registerServiceWorker } from "./pwa/register";
import "./styles/tokens.css";
import "./styles/native-feel.css";
import "./shell/safe-area.css";

registerServiceWorker();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
