import { NavLink } from "react-router-dom";

const NAV_ITEMS = [
  { to: "/", label: "Mi música" },
  { to: "/buscar", label: "Buscar" },
  { to: "/descubrir", label: "Descubrir" },
] as const;

export default function Sidebar() {
  return (
    <nav className="w-48 shrink-0 flex flex-col border-r border-zinc-800 py-4">
      {NAV_ITEMS.map(({ to, label }) => (
        <NavLink
          key={to}
          to={to}
          end
          className={({ isActive }) =>
            `px-6 py-3 text-sm transition-colors duration-150 ${
              isActive
                ? "text-white font-medium bg-zinc-800"
                : "text-zinc-400 hover:text-white hover:bg-zinc-900"
            }`
          }
        >
          {label}
        </NavLink>
      ))}
    </nav>
  );
}
