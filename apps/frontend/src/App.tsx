import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import AppLayout from "./components/layout/AppLayout";
import MiMusica from "./sections/MiMusica";
import Buscar from "./sections/Buscar";
import Descubrir from "./sections/Descubrir";

export default function App() {
  return (
    <BrowserRouter>
      <AppLayout>
        <Routes>
          <Route path="/" element={<MiMusica />} />
          <Route path="/buscar" element={<Buscar />} />
          <Route path="/descubrir" element={<Descubrir />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AppLayout>
    </BrowserRouter>
  );
}
