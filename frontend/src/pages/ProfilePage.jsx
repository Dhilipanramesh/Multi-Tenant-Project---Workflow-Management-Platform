import { ArrowLeft, AtSign, Mail, ShieldCheck, UserRound } from "lucide-react";
import { Link } from "react-router-dom";
import { useAuth } from "../state/AuthContext";

export default function ProfilePage() {
  const { user } = useAuth();
  return <div className="page-stack">
    <Link to="/" className="back-link"><ArrowLeft size={16} /> Back to overview</Link>
    <div className="page-title-row"><div><div className="eyebrow"><span /> ACCOUNT</div><h1>Profile</h1><p>Your identity and role in this organization.</p></div></div>
    <section className="panel profile-card">
      <div className="profile-banner"><div className="profile-large-avatar">{user?.full_name?.slice(0, 1).toUpperCase()}</div></div>
      <div className="profile-main"><div className="profile-name"><h2>{user?.full_name}</h2><span className="member-state enabled"><i /> Active</span></div><p>Member of your Flowspace workspace</p>
        <div className="profile-facts"><div><Mail size={16} /><span><small>Email address</small><strong>{user?.email}</strong></span></div><div><AtSign size={16} /><span><small>Username</small><strong>@{user?.username}</strong></span></div><div><ShieldCheck size={16} /><span><small>Organization role</small><strong>{user?.role?.replaceAll("_", " ") || "Team member"}</strong></span></div><div><UserRound size={16} /><span><small>Account type</small><strong>{user?.is_super_admin ? "Super admin" : "Organization member"}</strong></span></div></div>
      </div>
    </section>
    <div className="profile-settings-link"><p>Looking to update your account security?</p><Link to="/settings">Go to settings <ArrowLeft size={14} /></Link></div>
  </div>;
}
