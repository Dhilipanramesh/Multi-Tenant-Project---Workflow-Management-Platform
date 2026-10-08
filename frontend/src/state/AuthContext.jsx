import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import api from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [organizations, setOrganizations] = useState([]);
  const [organizationId, setOrganizationIdState] = useState(localStorage.getItem("organization_id") || "");
  const [loading, setLoading] = useState(Boolean(localStorage.getItem("access_token")));

  const setOrganizationId = useCallback((id) => {
    const value = String(id || "");
    setOrganizationIdState(value);
    if (value) localStorage.setItem("organization_id", value);
    else localStorage.removeItem("organization_id");
  }, []);

  const loadOrganizations = useCallback(async () => {
    const response = await api.get("/api/organizations");
    const available = response.data;
    setOrganizations(available);
    const selected = localStorage.getItem("organization_id");
    if (selected && available.some((item) => String(item.id) === selected)) {
      setOrganizationId(selected);
    } else if (available.length) {
      setOrganizationId(available[0].id);
    } else {
      setOrganizationId("");
    }
    return available;
  }, [setOrganizationId]);

  const acceptAuth = useCallback(async (data) => {
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    setUser(data.user);
    await loadOrganizations();
  }, [loadOrganizations]);

  const logout = useCallback(async () => {
    const refreshToken = localStorage.getItem("refresh_token");
    try {
      if (refreshToken) await api.post("/api/auth/logout", { refresh_token: refreshToken });
    } finally {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      localStorage.removeItem("organization_id");
      setUser(null);
      setOrganizations([]);
      setOrganizationIdState("");
    }
  }, []);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      setLoading(false);
      return;
    }
    Promise.all([api.get("/api/auth/me"), loadOrganizations()])
      .then(([profile]) => setUser(profile.data))
      .catch(() => {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, [loadOrganizations]);

  useEffect(() => {
    if (!user?.id || !organizationId) return;
    let alive = true;
    api.get(`/api/organizations/${organizationId}/members`)
      .then(({ data }) => {
        const membership = data.find((member) => member.user_id === user.id);
        if (alive && membership) setUser((current) => ({ ...current, role: membership.role }));
      })
      .catch(() => {
        if (alive) setUser((current) => current ? { ...current, role: current.is_super_admin ? "super_admin" : "team_member" } : current);
      });
    return () => { alive = false; };
  }, [organizationId, user?.id]);

  const value = useMemo(
    () => ({ user, organizations, organizationId, setOrganizationId, acceptAuth, logout, loading, loadOrganizations }),
    [user, organizations, organizationId, setOrganizationId, acceptAuth, logout, loading, loadOrganizations],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
