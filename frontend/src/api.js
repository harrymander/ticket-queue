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

export async function fetchAdminClientUrl(password, payload = {}) {
  return fetchAdminApi("client-url", password, payload);
}

export function validateTicket(ticket) {
  [
    ["id", "number"],
    ["token", "string"],
    ["name", "string"],
    ["position", "number"],
    ["timestamp", "number"],
  ].forEach(([prop, exp_type]) => {
    if (prop in ticket) {
      const type = typeof ticket[prop];
      if (type !== exp_type) {
        throw Error(
          `Invalid ticket object: property "${prop}" has invalid type; ` +
            `expected ${exp_type}, got ${type}`,
        );
      }
    } else {
      throw Error(`Invalid ticket object: missing property "${prop}"`);
    }
  });
}
