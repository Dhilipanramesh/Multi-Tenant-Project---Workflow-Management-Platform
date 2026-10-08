import { useState } from "react";
import { ArrowRight, Check, Layers3 } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import api, { errorMessage } from "../api/client";
import { useAuth } from "../state/AuthContext";
import { ErrorNotice } from "../components/Feedback";

function AuthFrame({ title, intro, children, footer }) {
  return <main className="auth-page">
    <div className="auth-decoration"><div className="auth-brand"><span className="brand-mark">F</span> flowspace</div><div className="auth-pitch"><div className="eyebrow light-eyebrow"><span /> PROJECTS THAT MOVE FORWARD</div><h1>Good work happens<br /><em>in flow.</em></h1><p>One calm workspace for your projects, your people, and everything you’re building together.</p><div className="auth-benefits"><span><Check size={15} /> Keep every project on track</span><span><Check size={15} /> Bring the whole team together</span><span><Check size={15} /> Make progress visible</span></div></div><div className="auth-copyright">© 2026 Flowspace workspace</div></div>
    <div className="auth-form-side"><div className="auth-mobile-brand"><span className="brand-mark">F</span> flowspace</div><div className="auth-form"><div className="auth-symbol"><Layers3 size={21} /></div><h2>{title}</h2><p className="muted">{intro}</p>{children}<div className="auth-footer">{footer}</div></div><div className="auth-legal">Secure workspace · Built for teams</div></div>
  </main>;
}

export function LoginPage() {
  const { acceptAuth } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  function change(event) { setForm((value) => ({ ...value, [event.target.name]: event.target.value })); }
  async function submit(event) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      const { data } = await api.post("/api/auth/login", form);
      await acceptAuth(data);
      navigate("/");
    } catch (requestError) { setError(errorMessage(requestError)); }
    finally { setBusy(false); }
  }
  return <AuthFrame title="Welcome back" intro="Sign in to your workspace to pick up where you left off." footer={<>New to Flowspace? <Link to="/register">Create an account <ArrowRight size={14} /></Link></>}>
    <ErrorNotice>{error}</ErrorNotice>
    <form className="form-stack" onSubmit={submit}>
      <label className="field"><span>Email address</span><input type="email" name="email" autoComplete="email" placeholder="you@company.com" value={form.email} onChange={change} required /></label>
      <label className="field"><span>Password</span><input type="password" name="password" autoComplete="current-password" placeholder="Enter your password" value={form.password} onChange={change} required /></label>
      <button className="button button-primary button-wide" disabled={busy}>{busy ? "Signing in..." : "Sign in"} <ArrowRight size={16} /></button>
    </form>
  </AuthFrame>;
}

export function RegisterPage() {
  const { acceptAuth } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ full_name: "", username: "", email: "", password: "", organization_name: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  function change(event) { setForm((value) => ({ ...value, [event.target.name]: event.target.value })); }
  async function submit(event) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      const { data } = await api.post("/api/auth/register", form);
      await acceptAuth(data);
      navigate("/");
    } catch (requestError) { setError(errorMessage(requestError)); }
    finally { setBusy(false); }
  }
  return <AuthFrame title="Create your workspace" intro="Get your team organized and moving in a few seconds." footer={<>Already have an account? <Link to="/login">Sign in <ArrowRight size={14} /></Link></>}>
    <ErrorNotice>{error}</ErrorNotice>
    <form className="form-stack" onSubmit={submit}>
      <div className="field-row">
        <label className="field"><span>Your name</span><input name="full_name" autoComplete="name" placeholder="Jordan Lee" value={form.full_name} onChange={change} required /></label>
        <label className="field"><span>Username</span><input name="username" autoComplete="username" minLength="3" placeholder="jordanlee" value={form.username} onChange={change} required /></label>
      </div>
      <label className="field"><span>Work email</span><input type="email" name="email" autoComplete="email" placeholder="you@company.com" value={form.email} onChange={change} required /></label>
      <label className="field"><span>Organization name</span><input name="organization_name" placeholder="Acme Studio" value={form.organization_name} onChange={change} required /></label>
      <label className="field"><span>Password</span><input type="password" name="password" autoComplete="new-password" minLength="10" placeholder="At least 10 characters" value={form.password} onChange={change} required /></label>
      <button className="button button-primary button-wide" disabled={busy}>{busy ? "Creating workspace..." : "Create account"} <ArrowRight size={16} /></button>
    </form>
  </AuthFrame>;
}
