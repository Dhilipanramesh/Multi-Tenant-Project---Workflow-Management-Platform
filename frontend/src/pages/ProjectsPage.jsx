import { ArrowDownUp, ArrowRight, BriefcaseBusiness, CalendarDays, Plus, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import api, { errorMessage } from "../api/client";
import { EmptyState, ErrorNotice, LoadingState } from "../components/Feedback";
import Modal from "../components/Modal";
import { useAuth } from "../state/AuthContext";

const initialForm = { name: "", description: "", status: "planning", start_date: "", due_date: "" };

export default function ProjectsPage() {
  const { organizationId, user } = useAuth();
  const [projects, setProjects] = useState([]);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [modal, setModal] = useState(false);
  const [form, setForm] = useState(initialForm);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const canCreate = ["organization_admin", "project_manager", "super_admin"].includes(user?.role);

  async function load() {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: String(page), page_size: "12" });
      if (search.trim()) params.set("search", search.trim());
      if (status) params.set("status", status);
      const { data } = await api.get(`/api/projects?${params}`);
      setProjects(data);
      setError("");
    } catch (requestError) { setError(errorMessage(requestError)); }
    finally { setLoading(false); }
  }
  useEffect(() => { load(); }, [organizationId, page, search, status]);
  const visibleProjects = useMemo(() => projects, [projects]);

  async function submit(event) {
    event.preventDefault();
    setError("");
    setBusy(true);
    const payload = { ...form, start_date: form.start_date ? new Date(form.start_date).toISOString() : null, due_date: form.due_date ? new Date(form.due_date).toISOString() : null };
    try {
      await api.post("/api/projects", payload);
      setModal(false);
      setForm(initialForm);
      await load();
    } catch (requestError) { setError(errorMessage(requestError)); }
    finally { setBusy(false); }
  }

  return <div className="page-stack">
    <div className="page-title-row"><div><div className="eyebrow"><span /> DELIVERY</div><h1>Projects</h1><p>Plan, organize, and keep your team moving forward.</p></div>{canCreate && <button className="button button-primary" onClick={() => setModal(true)}><Plus size={17} /> Create project</button>}</div>
    <ErrorNotice>{error}</ErrorNotice>
    <div className="toolbar">
      <label className="search-field"><Search size={17} /><input placeholder="Search projects..." value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} /><kbd>⌘ K</kbd></label>
      <label className="filter-field"><ArrowDownUp size={16} /><select value={status} onChange={(event) => { setStatus(event.target.value); setPage(1); }} aria-label="Filter project status"><option value="">All statuses</option><option value="planning">Planning</option><option value="active">Active</option><option value="on_hold">On hold</option><option value="completed">Completed</option><option value="archived">Archived</option></select></label>
    </div>
    {loading ? <LoadingState label="Loading projects..." /> : visibleProjects.length ? <div className="projects-grid">
      {visibleProjects.map((project, index) => <Link to={`/projects/${project.id}`} className={`project-card project-accent-${index % 4}`} key={project.id}>
        <div className="project-card-top"><div className="project-card-icon"><BriefcaseBusiness size={20} /></div><span className={`status-pill status-${project.status}`}>{project.status.replaceAll("_", " ")}</span></div>
        <h2>{project.name}</h2><p>{project.description || "A fresh space for your team’s work."}</p>
        <div className="project-card-footer"><span><CalendarDays size={14} />{project.due_date ? new Date(project.due_date).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }) : "No due date"}</span><span className="card-open">Open <ArrowRight size={14} /></span></div>
      </Link>)}
    </div> : <div className="panel"><EmptyState title={search || status ? "No matching projects" : "No projects yet"} description={search || status ? "Try adjusting your search or filters." : "Create your first project to get your team organized."} action={canCreate && !search && !status ? <button className="button button-primary" onClick={() => setModal(true)}><Plus size={16} /> Create project</button> : null} /></div>}
    <div className="pagination"><span>Page {page}</span><div><button className="button button-small button-outline" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>Previous</button><button className="button button-small button-outline" disabled={projects.length < 12} onClick={() => setPage((value) => value + 1)}>Next</button></div></div>
    {modal && <Modal title="Create a project" onClose={() => setModal(false)}><form className="form-stack modal-form" onSubmit={submit}>
      <label className="field"><span>Project name</span><input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} maxLength="200" placeholder="Website relaunch" required /></label>
      <label className="field"><span>Description <small>Optional</small></span><textarea rows="3" value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} placeholder="What is this project about?" /></label>
      <div className="field-row"><label className="field"><span>Status</span><select value={form.status} onChange={(event) => setForm({ ...form, status: event.target.value })}><option value="planning">Planning</option><option value="active">Active</option></select></label><label className="field"><span>Due date <small>Optional</small></span><input type="date" value={form.due_date} onChange={(event) => setForm({ ...form, due_date: event.target.value })} /></label></div>
      <div className="modal-actions"><button type="button" className="button button-outline" onClick={() => setModal(false)}>Cancel</button><button className="button button-primary" disabled={busy}>{busy ? "Creating..." : "Create project"}</button></div>
    </form></Modal>}
  </div>;
}
