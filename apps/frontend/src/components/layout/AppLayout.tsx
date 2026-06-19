import type { ReactNode } from "react";
import Header from "./Header";
import Sidebar from "./Sidebar";
import PlayerPanel from "../player/PlayerPanel";

interface AppLayoutProps {
  children: ReactNode;
}

export default function AppLayout({ children }: AppLayoutProps) {
  return (
    <div className="h-screen flex flex-col bg-zinc-950 text-white overflow-hidden">
      <Header />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto p-4">{children}</main>
        <PlayerPanel />
      </div>
    </div>
  );
}
