import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./shell/app-shell";
import { CapturePage } from "./capture/capture-page";
import { MetaPage } from "./meta/meta-page";
import { CAPTURE_ROUTE_PATH, META_ROUTE_PATH } from "./meta/meta-routes";

export function App() {
  return (
    <BrowserRouter>
      <AppShell>
        <Routes>
          <Route path={CAPTURE_ROUTE_PATH} element={<CapturePage />} />
          <Route path={META_ROUTE_PATH} element={<MetaPage />} />
          <Route path="*" element={<Navigate to={CAPTURE_ROUTE_PATH} replace />} />
        </Routes>
      </AppShell>
    </BrowserRouter>
  );
}
