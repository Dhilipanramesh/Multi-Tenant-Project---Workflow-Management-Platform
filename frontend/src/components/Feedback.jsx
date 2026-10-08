import { AlertCircle, CheckCircle2, Inbox } from "lucide-react";

export function ErrorNotice({ children, onRetry }) {
  if (!children) return null;
  return <div className="notice notice-error" role="alert"><AlertCircle size={18} /><span>{children}</span>{onRetry && <button className="text-button" onClick={onRetry}>Try again</button>}</div>;
}

export function SuccessNotice({ children }) {
  if (!children) return null;
  return <div className="notice notice-success" role="status"><CheckCircle2 size={18} /><span>{children}</span></div>;
}

export function EmptyState({ title = "Nothing here yet", description, action }) {
  return <div className="empty-state"><div className="empty-icon"><Inbox size={24} /></div><h3>{title}</h3>{description && <p>{description}</p>}{action}</div>;
}

export function LoadingState({ label = "Loading..." }) {
  return <div className="loading-state"><div className="loader" />{label}</div>;
}
