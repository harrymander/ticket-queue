const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "/api";

export async function fetchApi(endpoint, payload = {}) {
  return fetch(`${BACKEND_URL}/${endpoint}`, payload);
}

export async function fetchAdminApi(endpoint, password, payload = {}) {
  payload.headers = {
    ...payload.headers,
    Authorization: `Password ${btoa(password)}`,
  };
  return fetch(`${BACKEND_URL}/admin/${endpoint}`, payload);
}
