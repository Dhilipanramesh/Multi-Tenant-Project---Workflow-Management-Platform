import { KeyRound, Save, ShieldCheck, UserRound } from "lucide-react";
import { useState } from "react";
import api, { errorMessage } from "../api/client";
import { ErrorNotice, SuccessNotice } from "../components/Feedback";
import { useAuth } from "../state/AuthContext";

export default function SettingsPage() {
  const { user } = useAuth();
  const [form, setForm] = useState({ current_password: "", new_password: "" });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(event) {
    event.preventDefault();
    setError("");
    setSuccess("");
    setBusy(true);
    try {
      await api.post("/api/auth/change-password", form);
      setSuccess("Your password was changed. Please sign in again on other devices.");
      setForm({ current_password: "", new_password: "" });
    } catch (requestError) { setError(errorMessage(requestError)); }
    finally { setBusy(false); }
  }
  return <div className="page-stack">
    <div className="page-title-row"><div><div className="eyebrow"><span /> PREFERENCES</div><h1>Settings</h1><p>Manage your profile and account security.</p></div></div>
    <section className="panel settings-panel"><div className="settings-heading"><div className="settings-icon"><UserRound size={19} /></div><div><h2>Profile</h2><p>Your account details</p></div></div><div className="profile-detail"><span>Full name</span><strong>{user?.full_name}</strong></div><div className="profile-detail"><span>Email address</span><strong>{user?.email}</strong></div><div className="profile-detail"><span>Username</span><strong>@{user?.username}</strong></div><div className="profile-detail"><span>Account status</span><strong className="active-account"><i /> Active</strong></div></section>
    <section className="panel settings-panel"><div className="settings-heading"><div className="settings-icon green"><ShieldCheck size={19} /></div><div><h2>Password & security</h2><p>Choose a strong password you don’t use elsewhere.</p></div></div><ErrorNotice>{error}</ErrorNotice><SuccessNotice>{success}</SuccessNotice><form className="settings-form" onSubmit={submit}><label className="field"><span>Current password</span><input type="password" autoComplete="current-password" value={form.current_password} onChange={(event) => setForm({ ...form, current_password: event.target.value })} required /></label><label className="field"><span>New password</span><input type="password" autoComplete="new-password" minLength="10" value={form.new_password} onChange={(event) => setForm({ ...form, new_password: event.target.value })} required /><small>At least 10 characters</small></label><button className="button button-primary" disabled={busy}><KeyRound size={16} /> {busy ? "Updating..." : "Update password"}</button></form></section>
  </div>;
}
