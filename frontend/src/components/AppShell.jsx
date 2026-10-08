import { Bell, BriefcaseBusiness, ChevronDown, CircleHelp, LayoutDashboard, ListTodo, LogOut, Menu, Settings, Users, X } from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../state/AuthContext";

const links = [
  { to: "/", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/projects", label: "Projects", icon: BriefcaseBusiness },
  { to: "/tasks", label: "Task board", icon: ListTodo },
  { to: "/organizations", label: "Organizations", icon: Users },
  { to: "/members", label: "Members", icon: Users },
  { to: "/notifications", label: "Notifications", icon: Bell },
];

export default function AppShell() {
  const { user, organizations, organizationId, setOrganizationId, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const navigate = useNavigate();
  const selectedOrganization = organizations.find((item) => String(item.id) === String(organizationId));

  async function handleLogout() {
    await logout();
    navigate("/login");
  }

  return (
    <div className="app-shell">
      <aside className={`sidebar ${menuOpen ? "sidebar-open" : ""}`}>
        <div className="brand"><span className="brand-mark">F</span><span>flowspace</span><button className="mobile-close icon-button" onClick={() => setMenuOpen(false)} aria-label="Close menu"><X size={18} /></button></div>
        <div className="workspace-label">WORKSPACE</div>
        <label className="org-select-wrap">
          <span className="org-avatar">{(selectedOrganization?.name || "W").slice(0, 1).toUpperCase()}</span>
          <select value={organizationId} onChange={(event) => setOrganizationId(event.target.value)} aria-label="Select organization">
            {organizations.map((organization) => <option key={organization.id} value={organization.id}>{organization.name}</option>)}
          </select>
          <ChevronDown size={15} />
        </label>
        <nav className="side-nav" aria-label="Main navigation">
          {links.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end} onClick={() => setMenuOpen(false)} className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
              <Icon size={18} strokeWidth={1.8} /><span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-spacer" />
        <div className="side-bottom">
          <NavLink to="/settings" className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}><Settings size={18} /><span>Settings</span></NavLink>
          <a className="nav-link" href="mailto:support@example.com"><CircleHelp size={18} /><span>Help & support</span></a>
        </div>
        <div className="user-card">
          <button className="avatar profile-avatar-button" onClick={() => navigate("/profile")} aria-label="Open profile">{(user?.full_name || "U").slice(0, 1).toUpperCase()}</button>
          <div className="user-meta"><strong>{user?.full_name}</strong><span>{user?.email}</span></div>
          <button className="icon-button logout-button" onClick={handleLogout} title="Sign out" aria-label="Sign out"><LogOut size={17} /></button>
        </div>
      </aside>
      {menuOpen && <button className="backdrop" onClick={() => setMenuOpen(false)} aria-label="Close navigation" />}
      <main className="main-area">
        <header className="topbar">
          <button className="icon-button mobile-menu" onClick={() => setMenuOpen(true)} aria-label="Open navigation"><Menu size={21} /></button>
          <div className="breadcrumb">Workspace <span>/</span> <strong>{selectedOrganization?.name || "Organization"}</strong></div>
          <div className="top-actions">
            <NavLink to="/notifications" className="top-icon" aria-label="Notifications"><Bell size={19} /></NavLink>
            <div className="top-avatar">{(user?.full_name || "U").slice(0, 1).toUpperCase()}</div>
          </div>
        </header>
        <div className="page-content"><Outlet /></div>
      </main>
    </div>
  );
}
