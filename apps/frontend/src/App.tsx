import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import AppLayout from "./components/layout/AppLayout";
import LoginPage from "./components/auth/LoginPage";
import MiMusica from "./sections/MiMusica";
import Buscar from "./sections/Buscar";
import Descubrir from "./sections/Descubrir";
import Profile from "./sections/Profile";
import { useAuth } from "./hooks/useAuth";
import { AuthProvider } from "./context/AuthContext";
import { PlayerProvider } from "./context/PlayerContext";
import { FeedbackProvider } from "./context/FeedbackContext";

function AppContent() {
  const auth = useAuth();

  if (auth.isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-950">
        <span className="text-sm text-zinc-500">Loading...</span>
      </div>
    );
  }

  if (!auth.isAuthenticated) {
    return <LoginPage />;
  }

  return (
    <AuthProvider value={auth}>
      <PlayerProvider>
        <FeedbackProvider>
          <AppLayout>
            <Routes>
              <Route path="/" element={<MiMusica />} />
              <Route path="/buscar" element={<Buscar />} />
              <Route path="/descubrir" element={<Descubrir />} />
              <Route path="/perfil" element={<Profile />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </AppLayout>
        </FeedbackProvider>
      </PlayerProvider>
    </AuthProvider>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  );
}
