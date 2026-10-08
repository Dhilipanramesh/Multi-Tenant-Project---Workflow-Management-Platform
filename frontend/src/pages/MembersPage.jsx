import { Mail, Plus, Shield, UserRound, UserRoundCheck, UserRoundX } from "lucide-react";
import { useEffect, useState } from "react";
import api, { errorMessage } from "../api/client";
import { EmptyState, ErrorNotice, LoadingState } from "../components/Feedback";
import Modal from "../components/Modal";
import { useAuth } from "../state/AuthContext";

const roles = [
  ["organization_admin", "Organization admin"],
  ["project_manager", "Project manager"],
  ["team_member", "Team member"],
  ["viewer", "Viewer"],
];

export default function MembersPage() {
  const { organizationId, user } = useAuth();
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ email: "", role: "team_member" });
  const [busy, setBusy] = useState(false);
  const canManage = user?.role === "organization_admin";

  async function load() {
    if (!organizationId) return;
    setLoading(true);
    try {
      const { data } = await api.get(`/api/organizations/${organizationId}/members`);
      setMembers(data);
      setError("");
    } catch (requestError) { setError(errorMessage(requestError)); }
    finally { setLoading(false); }
  }
  useEffect(() => { load(); }, [organizationId]);

  async function addMember(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.post(`/api/organizations/${organizationId}/members`, form);
      setShowAdd(false);
      setForm({ email: "", role: "team_member" });
      await load();
    } catch (requestError) { setError(errorMessage(requestError)); }
    finally { setBusy(false); }
  }

  async function updateMember(member, updates) {
    try {
      const { data } = await api.patch(
        `/api/organizations/${organizationId}/members/${member.user_id}`,
        updates,
      );
      setMembers((current) => current.map((item) => item.user_id === member.user_id ? data : item));
    } catch (requestError) { setError(errorMessage(requestError)); }
  }

  async function removeMember(member) {
    if (!window.confirm(`Remove ${member.full_name} from this organization?`)) return;
    try {
      await api.delete(`/api/organizations/${organizationId}/members/${member.user_id}`);
      setMembers((current) => current.filter((item) => item.user_id !== member.user_id));
    } catch (requestError) { setError(errorMessage(requestError)); }
  }

  return <div className="page-stack">
    <div className="page-title-row"><div><div className="eyebrow"><span /> PEOPLE</div><h1>Members</h1><p>Manage the people and roles in your organization.</p></div>{canManage && <button className="button button-primary" onClick={() => setShowAdd(true)}><Plus size={16} /> Add member</button>}</div>
    <ErrorNotice>{error}</ErrorNotice>
    <section className="panel">
      <div className="section-heading"><div><h2>Organization members <span className="count-chip">{members.length}</span></h2><p>Only active members can access this workspace.</p></div><div className="member-summary"><UserRound size={16} /> {members.filter((member) => member.is_active).length} active</div></div>
      {loading ? <LoadingState label="Loading members..." /> : members.length ? <div className="members-table-wrap"><table className="members-table"><thead><tr><th>Member</th><th>Role</th><th>Status</th>{canManage && <th aria-label="Actions" />}</tr></thead><tbody>{members.map((member) => <tr key={member.user_id}><td><div className="member-person"><div className={`avatar member-avatar member-color-${member.user_id % 4}`}>{member.full_name.slice(0, 1).toUpperCase()}</div><div><strong>{member.full_name}{member.user_id === user?.id && <span className="you-tag">you</span>}</strong><span><Mail size={12} />{member.email}</span></div></div></td><td>{canManage && member.user_id !== user?.id ? <label className="role-select"><Shield size={13} /><select value={member.role} onChange={(event) => updateMember(member, { role: event.target.value })} aria-label={`Role for ${member.full_name}`}>{roles.map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label> : <span className="member-role"><Shield size={13} />{roles.find(([value]) => value === member.role)?.[1] || member.role.replaceAll("_", " ")}</span>}</td><td><span className={`member-state ${member.is_active ? "enabled" : "disabled"}`}><i />{member.is_active ? "Active" : "Inactive"}</span></td>{canManage && <td><div className="member-actions"><button className="icon-button" title={member.is_active ? "Deactivate member" : "Activate member"} aria-label={member.is_active ? "Deactivate member" : "Activate member"} onClick={() => updateMember(member, { is_active: !member.is_active })}>{member.is_active ? <UserRoundX size={16} /> : <UserRoundCheck size={16} />}</button>{member.user_id !== user?.id && <button className="icon-button remove-member" onClick={() => removeMember(member)} title="Remove member" aria-label="Remove member"><UserRoundX size={16} /></button>}</div></td>}</tr>)}</tbody></table></div> : <EmptyState title="No members found" description="Invite your teammates to collaborate in this workspace." />}
    </section>
    {showAdd && <Modal title="Add a member" onClose={() => setShowAdd(false)}><form className="form-stack modal-form" onSubmit={addMember}><label className="field"><span>Member email</span><input type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} placeholder="teammate@company.com" required /><small>They need an existing Flowspace account.</small></label><label className="field"><span>Organization role</span><select value={form.role} onChange={(event) => setForm({ ...form, role: event.target.value })}>{roles.filter(([value]) => value !== "organization_admin").map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label><div className="modal-actions"><button type="button" className="button button-outline" onClick={() => setShowAdd(false)}>Cancel</button><button className="button button-primary" disabled={busy}>{busy ? "Adding..." : "Add member"}</button></div></form></Modal>}
  </div>;
}
