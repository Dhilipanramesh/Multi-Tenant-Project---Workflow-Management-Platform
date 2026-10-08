import { ArrowLeft, CalendarDays, Check, ChevronDown, MessageSquare, Send } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api, { errorMessage } from "../api/client";
import { ErrorNotice, LoadingState } from "../components/Feedback";
import { useAuth } from "../state/AuthContext";

const statuses = ["backlog", "todo", "in_progress", "blocked", "review", "done", "cancelled"];
const priorities = ["low", "medium", "high", "urgent"];

export default function TaskDetailPage() {
  const { taskId } = useParams();
  const { organizationId, user } = useAuth();
  const [task, setTask] = useState(null);
  const [comments, setComments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [comment, setComment] = useState("");
  const [saving, setSaving] = useState(false);
  async function load() {
    setLoading(true);
    try {
      const [taskResponse, commentResponse] = await Promise.all([
        api.get(`/api/tasks/${taskId}`),
        api.get(`/api/tasks/${taskId}/comments`),
      ]);
      setTask(taskResponse.data);
      setComments(commentResponse.data);
      setError("");
    } catch (requestError) { setError(errorMessage(requestError)); }
    finally { setLoading(false); }
  }
  useEffect(() => { load(); }, [taskId, organizationId]);
  async function update(values) {
    setSaving(true);
    setError("");
    try {
      const { data } = await api.patch(`/api/tasks/${taskId}`, values);
      setTask(data);
    } catch (requestError) { setError(errorMessage(requestError)); }
    finally { setSaving(false); }
  }
  async function addComment(event) {
    event.preventDefault();
    if (!comment.trim()) return;
    try {
      const { data } = await api.post(`/api/tasks/${taskId}/comments`, { body: comment });
      setComments((current) => [...current, data]);
      setComment("");
    } catch (requestError) { setError(errorMessage(requestError)); }
  }
  if (loading) return <LoadingState label="Loading task..." />;
  if (!task) return <div className="page-stack"><ErrorNotice>{error || "Task not found."}</ErrorNotice><Link className="back-link" to="/tasks"><ArrowLeft size={16} /> Back to task board</Link></div>;
  return <div className="page-stack">
    <Link to={`/tasks?project_id=${task.project_id}`} className="back-link"><ArrowLeft size={16} /> Back to task board</Link>
    <ErrorNotice>{error}</ErrorNotice>
    <section className="panel task-detail-panel">
      <div className="task-detail-top"><span className="task-id">TASK-{task.id}</span><span className="detail-saving">{saving ? "Saving…" : "Changes save immediately"}</span></div>
      <h1 className="task-detail-title">{task.title}</h1>
      <p className="task-detail-description">{task.description || "No description has been added to this task."}</p>
      <div className="task-detail-fields">
        <label className="detail-field"><span>Status</span><div className="detail-select-wrap"><select value={task.status} onChange={(event) => update({ status: event.target.value })} aria-label="Task status">{statuses.map((value) => <option value={value} key={value}>{value.replaceAll("_", " ")}</option>)}</select><ChevronDown size={14} /></div></label>
        <label className="detail-field"><span>Priority</span><div className="detail-select-wrap"><select value={task.priority} onChange={(event) => update({ priority: event.target.value })} aria-label="Task priority">{priorities.map((value) => <option value={value} key={value}>{value}</option>)}</select><ChevronDown size={14} /></div></label>
        <div className="detail-field"><span>Assignee</span><strong>{task.assignee_id ? `Member #${task.assignee_id}` : "Unassigned"}</strong></div>
        <div className="detail-field"><span>Due date</span><strong><CalendarDays size={14} />{task.due_date ? new Date(task.due_date).toLocaleDateString() : "No due date"}</strong></div>
        <div className="detail-field"><span>Estimated hours</span><strong>{task.estimated_hours ?? "Not set"}</strong></div>
        <div className="detail-field"><span>Reporter</span><strong>Member #{task.reporter_id}</strong></div>
      </div>
      <div className="task-description-edit"><label className="field"><span>Description</span><textarea rows="4" defaultValue={task.description || ""} onBlur={(event) => event.target.value !== (task.description || "") && update({ description: event.target.value })} placeholder="Add context, acceptance criteria, or notes..." /></label></div>
      <div className="task-detail-footer"><span>Created {new Date(task.created_at).toLocaleDateString()}</span><span>Updated {new Date(task.updated_at).toLocaleDateString()}</span></div>
    </section>
    <section className="panel">
      <div className="section-heading"><div><h2>Comments <span className="count-chip">{comments.length}</span></h2><p>Keep the conversation close to the work.</p></div><MessageSquare size={18} className="muted-icon" /></div>
      <div className="comment-list">{comments.map((item) => <article className="comment-item" key={item.id}><div className="avatar small-avatar">{item.author_id === user?.id ? user.full_name.slice(0, 1) : "T"}</div><div><div className="comment-meta"><strong>{item.author_id === user?.id ? "You" : `Member #${item.author_id}`}</strong><time>{new Date(item.created_at).toLocaleString()}</time></div><p>{item.body}</p></div></article>)}</div>
      <form className="comment-form" onSubmit={addComment}><div className="avatar small-avatar">{user?.full_name?.slice(0, 1)}</div><input value={comment} onChange={(event) => setComment(event.target.value)} placeholder="Write a comment... Mention with @username" aria-label="Task comment" /><button className="icon-submit" disabled={!comment.trim()} aria-label="Send comment"><Send size={17} /></button></form>
    </section>
  </div>;
}
