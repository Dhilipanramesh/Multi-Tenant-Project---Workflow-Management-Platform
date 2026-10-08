import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
  headers: { "Content-Type": "application/json" },
});

let refreshRequest;

api.interceptors.request.use((config) => {
  const accessToken = localStorage.getItem("access_token");
  const organizationId = localStorage.getItem("organization_id");
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`;
  if (organizationId) config.headers["X-Organization-ID"] = organizationId;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (requestError) => {
    const original = requestError.config;
    if (
      requestError.response?.status === 401 &&
      original &&
      !original._retried &&
      !original.url?.includes("/api/auth/")
    ) {
      const refreshToken = localStorage.getItem("refresh_token");
      if (refreshToken) {
        original._retried = true;
        try {
          refreshRequest ||= axios.post(
            `${api.defaults.baseURL}/api/auth/refresh`,
            { refresh_token: refreshToken },
          );
          const { data } = await refreshRequest;
          localStorage.setItem("access_token", data.access_token);
          localStorage.setItem("refresh_token", data.refresh_token);
          refreshRequest = undefined;
          original.headers.Authorization = `Bearer ${data.access_token}`;
          return api(original);
        } catch {
          refreshRequest = undefined;
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
          localStorage.removeItem("organization_id");
        }
      }
    }
    const body = requestError.response?.data?.error;
    requestError.userMessage =
      body?.message ||
      (requestError.response ? "Something went wrong. Please try again." : "Unable to reach the server.");
    requestError.code = body?.code || "NETWORK_ERROR";
    return Promise.reject(requestError);
  },
);

export function errorMessage(error) {
  return error?.userMessage || error?.response?.data?.error?.message || error?.message || "Unexpected error.";
}

export default api;
