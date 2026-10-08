import { ArrowRight, BriefcaseBusiness, CheckCircle2, CircleAlert, ListTodo, Plus, Users } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api/client";
import { ErrorNotice, LoadingState } from "../components/Feedback";
import { useAuth } from "../state/AuthContext";

const count = (value) => new Intl.NumberFormat().format(value || 0);

export default function DashboardPage() {
  const { user, organizationId } = useAuth();
  const [data, setData] = useState(null);
  const [projects, setProjects] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let alive = true;
    setLoading(true);
    Promise.all([api.get("/api/dashboard"), api.get("/api/projects?page=1&page_size=5")])
      .then(([summary, projectResponse]) => {
        if (alive) { setData(summary.data); setProjects(projectResponse.data); setError(""); }
      })
      .catch((requestError) => { if (alive) setError(requestError.userMessage || "Could not load your overview."); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [organizationId]);

  const cards = data?.role === "organization_admin"
    ? [
      { label: "Total projects", value: data.total_projects, icon: BriefcaseBusiness, tone: "violet" },
      { label: "Active projects", value: data.active_projects, icon: ListTodo, tone: "blue" },
      { label: "Team members", value: data.active_users, icon: Users, tone: "green" },
      { label: "Overdue tasks", value: data.overdue_tasks, icon: CircleAlert, tone: "amber" },
    ]
    : data?.role === "project_manager"
      ? [
        { label: "My projects", value: data.my_projects, icon: BriefcaseBusiness, tone: "violet" },
        { label: "Open tasks", value: data.open_tasks, icon: ListTodo, tone: "blue" },
        { label: "Completed tasks", value: data.completed_tasks, icon: CheckCircle2, tone: "green" },
        { label: "Overdue tasks", value: data.overdue_tasks, icon: CircleAlert, tone: "amber" },
      ]
      : [
        { label: "My tasks", value: data?.my_tasks?.length, icon: ListTodo, tone: "violet" },
        { label: "Due today", value: data?.tasks_due_today, icon: CircleAlert, tone: "blue" },
        { label: "Recently completed", value: data?.recently_completed_tasks?.length, icon: CheckCircle2, tone: "green" },
        { label: "Overdue tasks", value: data?.overdue_tasks, icon: CircleAlert, tone: "amber" },
      ];

  return <div className="page-stack">
    <div className="welcome-banner">
      <div><div className="eyebrow"><span /> YOUR WORKSPACE</div><h1>Good to see you, {user?.full_name?.split(" ")[0]} <span className="wave">✦</span></h1><p>Here’s what’s happening across your team today.</p></div>
      <Link to="/projects" className="button button-white"><Plus size={16} /> New project</Link>
      <div className="banner-orbit orbit-one" /><div className="banner-orbit orbit-two" />
    </div>
    <ErrorNotice>{error}</ErrorNotice>
    {loading ? <LoadingState label="Loading your overview..." /> : <section className="stats-grid">
      {cards.map(({ label, value, icon: Icon, tone }) => <article className="stat-card" key={label}><div className={`stat-icon ${tone}`}><Icon size={18} /></div><div><div className="stat-value">{count(value)}</div><div className="stat-label">{label}</div></div></article>)}
    </section>}
    <section className="panel">
      <div className="section-heading"><div><h2>Projects</h2><p>Your team’s latest workspaces</p></div><Link className="quiet-link" to="/projects">View all <ArrowRight size={15} /></Link></div>
      {loading ? <LoadingState label="Loading projects..." /> : projects.length ? <div className="project-list">
        {projects.map((project) => <Link className="project-row" to={`/projects/${project.id}`} key={project.id}>
          <div className="project-avatar">{project.name.slice(0, 1).toUpperCase()}</div><div className="project-row-main"><strong>{project.name}</strong><span>{project.description || "No description provided"}</span></div>
          <span className={`status-pill status-${project.status}`}>{project.status.replaceAll("_", " ")}</span><ArrowRight className="row-arrow" size={17} />
        </Link>)}
      </div> : <div className="empty-inline"><p>No projects yet. Create one to get started.</p><Link to="/projects" className="quiet-link">Open projects <ArrowRight size={15} /></Link></div>}
    </section>
    {data?.tasks_by_priority && <section className="panel priority-panel"><div className="section-heading"><div><h2>Tasks by priority</h2><p>Current workload across your organization</p></div></div><div className="priority-bars">{["urgent", "high", "medium", "low"].map((priority) => {
      const total = Object.values(data.tasks_by_priority).reduce((sum, n) => sum + n, 0) || 1;
      const value = data.tasks_by_priority[priority] || 0;
      return <div className="priority-line" key={priority}><span className={`priority-dot ${priority}`} /> <span>{priority}</span><div className="bar-track"><div className={`bar-fill ${priority}`} style={{ width: `${Math.max(value / total * 100, value ? 6 : 0)}%` }} /></div><strong>{value}</strong></div>;
    })}</div></section>}
  </div>;
}
