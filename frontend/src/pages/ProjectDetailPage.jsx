import { ArrowLeft, CalendarDays, Check, ChevronDown, CirclePlus, Columns3, MessageSquare, Plus, Send } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api, { errorMessage } from "../api/client";
import { EmptyState, ErrorNotice, LoadingState } from "../components/Feedback";
import Modal from "../components/Modal";
import { useAuth } from "../state/AuthContext";

const statusNames = { backlog: "Backlog", todo: "To do", in_progress: "In progress", blocked: "Blocked", review: "In review", done: "Done", cancelled: "Cancelled" };

export default function ProjectDetailPage() {
  const { projectId } = useParams();
  const { organizationId, user } = useAuth();
  const [project, setProject] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [comments, setComments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showTask, setShowTask] = useState(false);
  const [taskTitle, setTaskTitle] = useState("");
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const canEdit = ["organization_admin", "project_manager", "super_admin"].includes(user?.role);

  async function load() {
    setLoading(true);
    try {
      const [projectResult, tasksResult, commentsResult] = await Promise.all([
        api.get(`/api/projects/${projectId}`),
        api.get(`/api/projects/${projectId}/tasks?page_size=100`),
        api.get(`/api/projects/${projectId}/comments`),
      ]);
      setProject(projectResult.data);
      setTasks(tasksResult.data);
      setComments(commentsResult.data);
      setError("");
    } catch (requestError) { setError(errorMessage(requestError)); }
    finally { setLoading(false); }
  }
  useEffect(() => { load(); }, [projectId, organizationId]);

  async function createTask(event) {
    event.preventDefault();
    setBusy(true);
    try {
      await api.post(`/api/projects/${projectId}/tasks`, { title: taskTitle });
      setTaskTitle("");
      setShowTask(false);
      await load();
    } catch (requestError) { setError(errorMessage(requestError)); }
    finally { setBusy(false); }
  }
  async function changeTaskStatus(task, next) {
    try {
      await api.patch(`/api/tasks/${task.id}`, { status: next });
      await load();
    } catch (requestError) { setError(errorMessage(requestError)); }
  }
  async function addComment(event) {
    event.preventDefault();
    if (!comment.trim()) return;
    try {
      await api.post(`/api/projects/${projectId}/comments`, { body: comment });
      setComment("");
      await load();
    } catch (requestError) { setError(errorMessage(requestError)); }
  }
  if (loading) return <LoadingState label="Loading project..." />;
  if (!project) return <div className="page-stack"><ErrorNotice>{error || "Project not found."}</ErrorNotice><Link to="/projects" className="quiet-link"><ArrowLeft size={16} /> Back to projects</Link></div>;
  return <div className="page-stack">
    <Link to="/projects" className="back-link"><ArrowLeft size={16} /> All projects</Link>
    <ErrorNotice>{error}</ErrorNotice>
    <section className="project-hero panel">
      <div className="project-hero-main"><div className="project-card-icon"><span>{project.name.slice(0, 1).toUpperCase()}</span></div><div><div className="eyebrow"><span /> PROJECT WORKSPACE</div><h1>{project.name}</h1><p>{project.description || "No project description has been added."}</p></div></div>
      <div className="project-hero-meta"><span className={`status-pill status-${project.status}`}>{project.status.replaceAll("_", " ")}</span><span><CalendarDays size={15} />{project.due_date ? `Due ${new Date(project.due_date).toLocaleDateString()}` : "No due date"}</span><Link className="quiet-link" to={`/tasks?project_id=${project.id}`}><Columns3 size={14} /> Board</Link></div>
    </section>
    <section className="panel">
      <div className="section-heading"><div><h2>Task list <span className="count-chip">{tasks.length}</span></h2><p>Work tracked in this project</p></div>{canEdit && <button className="button button-primary button-small" onClick={() => setShowTask(true)}><Plus size={15} /> Add task</button>}</div>
      {tasks.length ? <div className="task-table-wrap"><table className="task-table"><thead><tr><th>Task</th><th>Status</th><th>Priority</th><th>Assignee</th></tr></thead><tbody>{tasks.map((task) => <tr key={task.id}><td><span className={`task-check ${task.status === "done" ? "checked" : ""}`}>{task.status === "done" && <Check size={12} />}</span><div className="task-cell"><strong>{task.title}</strong><small>{task.description || `Task #${task.id}`}</small></div></td><td><label className="inline-select"><select value={task.status} onChange={(event) => changeTaskStatus(task, event.target.value)} aria-label={`Status for ${task.title}`}>{Object.entries(statusNames).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select><ChevronDown size={13} /></label></td><td><span className={`priority-label ${task.priority}`}><i />{task.priority}</span></td><td>{task.assignee_id ? `Member #${task.assignee_id}` : <span className="muted">Unassigned</span>}</td></tr>)}</tbody></table></div> : <EmptyState title="No tasks in this project" description="Break your project into tasks and keep the work moving." action={canEdit && <button className="button button-primary" onClick={() => setShowTask(true)}><CirclePlus size={16} /> Add first task</button>} />}
    </section>
    <section className="panel">
      <div className="section-heading"><div><h2>Discussion <span className="count-chip">{comments.length}</span></h2><p>Updates and notes from your team</p></div><MessageSquare size={18} className="muted-icon" /></div>
      <div className="comment-list">{comments.map((item) => <article className="comment-item" key={item.id}><div className="avatar small-avatar">{item.author_id === user?.id ? user.full_name.slice(0, 1) : "T"}</div><div><div className="comment-meta"><strong>{item.author_id === user?.id ? "You" : `Member #${item.author_id}`}</strong><time>{new Date(item.created_at).toLocaleString()}</time></div><p>{item.body}</p></div></article>)}</div>
      <form className="comment-form" onSubmit={addComment}><div className="avatar small-avatar">{user?.full_name?.slice(0, 1)}</div><input value={comment} onChange={(event) => setComment(event.target.value)} placeholder="Share an update... Use @username to mention someone" aria-label="Project comment" /><button className="icon-submit" disabled={!comment.trim()} aria-label="Send comment"><Send size={17} /></button></form>
    </section>
    {showTask && <Modal title="Add a task" onClose={() => setShowTask(false)}><form className="form-stack modal-form" onSubmit={createTask}><label className="field"><span>Task title</span><input autoFocus value={taskTitle} onChange={(event) => setTaskTitle(event.target.value)} maxLength="200" placeholder="What needs to be done?" required /></label><div className="modal-actions"><button type="button" className="button button-outline" onClick={() => setShowTask(false)}>Cancel</button><button className="button button-primary" disabled={busy}>{busy ? "Adding..." : "Add task"}</button></div></form></Modal>}
  </div>;
}
