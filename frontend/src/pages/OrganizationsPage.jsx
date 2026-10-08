import { ArrowRight, Building2, Plus, Users } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import api, { errorMessage } from "../api/client";
import { ErrorNotice } from "../components/Feedback";
import Modal from "../components/Modal";
import { useAuth } from "../state/AuthContext";

export default function OrganizationsPage() {
  const { organizations, organizationId, setOrganizationId, loadOrganizations } = useAuth();
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const { data } = await api.post("/api/organizations", { name });
      await loadOrganizations();
      setOrganizationId(data.id);
      setCreating(false);
      setName("");
    } catch (requestError) { setError(errorMessage(requestError)); }
    finally { setBusy(false); }
  }
  return <div className="page-stack">
    <div className="page-title-row"><div><div className="eyebrow"><span /> YOUR TEAMS</div><h1>Organizations</h1><p>Switch between the teams and workspaces you belong to.</p></div><button className="button button-primary" onClick={() => setCreating(true)}><Plus size={17} /> New organization</button></div>
    <ErrorNotice>{error}</ErrorNotice>
    <div className="org-grid">{organizations.map((organization, index) => <article key={organization.id} className={`org-card ${String(organization.id) === String(organizationId) ? "selected" : ""}`}><div className={`org-card-icon color-${index % 4}`}><Building2 size={21} /></div><div className="org-card-copy"><h2>{organization.name}</h2><p><Users size={14} /> Organization workspace</p></div><button className="button button-outline button-small" onClick={() => setOrganizationId(organization.id)}>{String(organization.id) === String(organizationId) ? "Current" : "Switch"} <ArrowRight size={14} /></button><Link to="/" className="org-card-overlay" aria-label={`Open ${organization.name}`} onClick={() => setOrganizationId(organization.id)} /></article>)}</div>
    {creating && <Modal title="Create an organization" onClose={() => setCreating(false)}><form className="form-stack modal-form" onSubmit={submit}><label className="field"><span>Organization name</span><input autoFocus value={name} onChange={(event) => setName(event.target.value)} maxLength="160" placeholder="Acme Studio" required /></label><p className="form-hint">You’ll be added as the organization admin.</p><div className="modal-actions"><button type="button" className="button button-outline" onClick={() => setCreating(false)}>Cancel</button><button className="button button-primary" disabled={busy}>{busy ? "Creating..." : "Create organization"}</button></div></form></Modal>}
  </div>;
}
