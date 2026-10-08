import { Bell, Check, CheckCheck, CircleDot } from "lucide-react";
import { useEffect, useState } from "react";
import api, { errorMessage } from "../api/client";
import { EmptyState, ErrorNotice, LoadingState } from "../components/Feedback";
import { useAuth } from "../state/AuthContext";

export default function NotificationsPage() {
  const { organizationId } = useAuth();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  async function load() {
    setLoading(true);
    try { const { data } = await api.get("/api/notifications?page_size=50"); setItems(data); setError(""); }
    catch (requestError) { setError(errorMessage(requestError)); }
    finally { setLoading(false); }
  }
  useEffect(() => { load(); }, [organizationId]);
  async function markRead(item) {
    try { const { data } = await api.patch(`/api/notifications/${item.id}/read`); setItems((current) => current.map((entry) => entry.id === item.id ? data : entry)); }
    catch (requestError) { setError(errorMessage(requestError)); }
  }
  async function markAllRead() {
    try { await api.patch("/api/notifications/read-all"); setItems((current) => current.map((item) => ({ ...item, is_read: true }))); }
    catch (requestError) { setError(errorMessage(requestError)); }
  }
  return <div className="page-stack">
    <div className="page-title-row"><div><div className="eyebrow"><span /> UPDATES</div><h1>Notifications</h1><p>Stay in the loop on changes across your workspace.</p></div>{items.some((item) => !item.is_read) && <button className="button button-outline" onClick={markAllRead}><CheckCheck size={16} /> Mark all read</button>}</div>
    <ErrorNotice>{error}</ErrorNotice>
    <section className="panel notification-panel">{loading ? <LoadingState label="Loading notifications..." /> : items.length ? <div className="notification-list">{items.map((item) => <article key={item.id} className={`notification-item ${item.is_read ? "" : "unread"}`}><div className={`notification-icon ${item.is_read ? "" : "new"}`}><Bell size={17} /></div><div className="notification-copy"><strong>{item.kind.replaceAll("_", " ")}</strong><p>{item.message}</p><time>{new Date(item.created_at).toLocaleString()}</time></div>{!item.is_read && <button className="icon-button read-button" onClick={() => markRead(item)} title="Mark as read" aria-label="Mark notification as read"><Check size={17} /></button>}<span className="read-state">{item.is_read ? null : <CircleDot size={12} />}</span></article>)}</div> : <EmptyState title="You’re all caught up" description="New assignments, mentions, and updates will show up here." />}</section>
  </div>;
}
