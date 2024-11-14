const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "/api";

export async function fetchApi(endpoint, payload = {}) {
  return fetch(`${BACKEND_URL}/${endpoint}`, payload);
}

export async function newTicket(name) {
  return fetchApi("tickets", {
    method: "POST",
    body: JSON.stringify({ name }),
    headers: {
      "Content-Type": "application/json",
    },
  });
}

export async function deleteTicket(id, token) {
  return fetchApi(`ticket/${id}`, {
    method: "DELETE",
    headers: {
      Authorization: `Token ${token}`,
    },
  });
}

export async function fetchTicket(id, token) {
  const q = new URLSearchParams({ token });
  return fetchApi(`ticket/${id}?${q.toString()}`);
}

export async function fetchAdminApi(endpoint, password, payload = {}) {
  payload.headers = {
    ...payload.headers,
    Authorization: `Password ${btoa(password)}`,
  };
  return fetch(`${BACKEND_URL}/admin/${endpoint}`, payload);
}

export function validateTicket(ticket) {
  [
    ["id", "number"],
    ["token", "string"],
    ["name", "string"],
    ["position", "number"],
    ["timestamp", "number"],
  ].forEach(([prop, type]) => {
    const actual = typeof ticket[prop];
    if (actual !== type) {
      throw Error(
        `Invalid ticket object: property ${prop} has invalid type; ` +
          `expected ${type}, got ${actual}`,
      );
    }
  });
}
