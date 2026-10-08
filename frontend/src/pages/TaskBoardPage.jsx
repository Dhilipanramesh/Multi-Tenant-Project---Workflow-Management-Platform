import { ArrowLeft, ChevronDown, Search, SlidersHorizontal } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import api, { errorMessage } from "../api/client";
import { ErrorNotice, LoadingState } from "../components/Feedback";
import { useAuth } from "../state/AuthContext";

const columns = [
  { status: "backlog", label: "Backlog" },
  { status: "todo", label: "To do" },
  { status: "in_progress", label: "In progress" },
  { status: "review", label: "In review" },
  { status: "done", label: "Done" },
];
const transitions = {
  backlog: ["todo", "cancelled"], todo: ["backlog", "in_progress", "cancelled"],
  in_progress: ["todo", "blocked", "review", "cancelled"], blocked: ["in_progress", "cancelled"],
  review: ["in_progress", "done"], done: [], cancelled: ["todo"],
};

export default function TaskBoardPage() {
  const { organizationId } = useAuth();
  const [searchParams] = useSearchParams();
  const [tasks, setTasks] = useState([]);
  const [search, setSearch] = useState("");
  const [priority, setPriority] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const projectId = searchParams.get("project_id");
  async function load() {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page_size: "100" });
      if (projectId) params.set("project_id", projectId);
      if (search.trim()) params.set("search", search.trim());
      if (priority) params.set("priority", priority);
      const { data } = await api.get(`/api/tasks?${params}`);
      setTasks(data);
      setError("");
    } catch (requestError) { setError(errorMessage(requestError)); }
    finally { setLoading(false); }
  }
  useEffect(() => { load(); }, [organizationId, projectId, search, priority]);
  async function move(task, nextStatus) {
    try {
      await api.patch(`/api/tasks/${task.id}`, { status: nextStatus });
      await load();
    } catch (requestError) { setError(errorMessage(requestError)); }
  }
  return <div className="page-stack">
    <Link to={projectId ? `/projects/${projectId}` : "/projects"} className="back-link"><ArrowLeft size={16} /> {projectId ? "Back to project" : "Projects"}</Link>
    <div className="page-title-row board-title"><div><div className="eyebrow"><span /> WORKFLOW</div><h1>Task board</h1><p>Move tasks through your team’s workflow.</p></div></div>
    <ErrorNotice>{error}</ErrorNotice>
    <div className="toolbar board-toolbar"><label className="search-field"><Search size={17} /><input placeholder="Find a task..." value={search} onChange={(event) => setSearch(event.target.value)} /></label><label className="filter-field"><SlidersHorizontal size={16} /><select value={priority} onChange={(event) => setPriority(event.target.value)} aria-label="Filter priority"><option value="">All priorities</option><option value="urgent">Urgent</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select><ChevronDown size={13} /></label></div>
    {loading ? <LoadingState label="Loading tasks..." /> : <div className="kanban-board">{columns.map((column) => {
      const columnTasks = tasks.filter((task) => task.status === column.status);
      return <section className="kanban-column" key={column.status}><header className="kanban-heading"><span className={`column-indicator indicator-${column.status}`} /><h2>{column.label}</h2><span className="count-chip">{columnTasks.length}</span></header>
        <div className="kanban-cards">{columnTasks.map((task) => <article className="kanban-card" key={task.id}><div className="kanban-card-top"><span className={`priority-label ${task.priority}`}><i />{task.priority}</span><Link to={`/tasks/${task.id}`} className="task-id" aria-label={`Open task ${task.id}`}>#{task.id}</Link></div><Link to={`/tasks/${task.id}`} className="kanban-task-title">{task.title}</Link><p>{task.description || "No description"}</p><div className="kanban-card-footer"><span className="assignee-mini">{task.assignee_id ? `U${task.assignee_id}` : "—"}</span><label className="move-select"><span>Move</span><select value={task.status} onChange={(event) => move(task, event.target.value)} aria-label={`Move ${task.title}`}>{[task.status, ...(transitions[task.status] || [])].map((status) => <option key={status} value={status}>{status.replaceAll("_", " ")}</option>)}</select><ChevronDown size={12} /></label></div></article>)}{!columnTasks.length && <div className="kanban-empty">No tasks here</div>}</div>
      </section>;
    })}</div>}
  </div>;
}
