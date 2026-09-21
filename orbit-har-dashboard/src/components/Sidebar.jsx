import { NavLink } from "react-router-dom";

const LINKS = [
  { to: "/", label: "Monitoring", icon: "📊", end: true },
  { to: "/experiments", label: "Experiments", icon: "🧪" },
  { to: "/logs", label: "Logs", icon: "📜" },
  { to: "/videos", label: "Videos", icon: "🎥" },
  { to: "/text-files", label: "Text Files", icon: "📄" },
  {
    to: "/human-mesh",
    label: "3D Human Mesh",
    icon: "🧍",
  },
];

function Sidebar() {
  return (
    <aside className="sidebar">

      <div className="sidebar-logo">
        <img
          src="/isro-logo.png"
          alt="ISRO"
        />
      </div>

      <nav className="sidebar-nav">
        {LINKS.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.end}
            className={({ isActive }) =>
              isActive
                ? "sidebar-link active"
                : "sidebar-link"
            }
          >
            <span className="sidebar-icon">
              {link.icon}
            </span>

            <span>{link.label}</span>
          </NavLink>
        ))}
      </nav>

    </aside>
  );
}

export default Sidebar;