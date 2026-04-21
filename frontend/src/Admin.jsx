import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import QRCode from "qrcode";
import * as Api from "./api";
import { waitTimeMinutesString } from "./utils";

function PasswordEntry({ logIn }) {
  const [passwordInput, setPasswordInput] = useState("");
  const [loginState, setLoginState] = useState("logged-out");

  function tryLogIn() {
    setLoginState("logging-in");
    setPasswordInput("");
    Api.fetchAdminApi("tickets", passwordInput).then((r) => {
      if (r.status == 200) {
        logIn(passwordInput);
      } else if (r.status === 401) {
        setLoginState("invalid-password");
      } else {
        setLoginState("unknown-error");
      }
    });
  }

  if (loginState === "logging-in") {
    return <p>Logging in...</p>;
  }

  return (
    <>
      <form>
        <input
          placeholder="Admin password"
          type="password"
          onChange={(e) => setPasswordInput(e.target.value)}
          value={passwordInput}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              tryLogIn();
            }
          }}
          autoComplete="off"
        />
        <button
          className="button button--primary"
          onClick={tryLogIn}
          type="button"
        >
          Log in
        </button>
      </form>
      {loginState !== "logged-out" && (
        <p>
          {loginState === "invalid-password"
            ? "Incorrect password!"
            : "An unknown error occurrred!"}
        </p>
      )}
    </>
  );
}

function popPasswordFromSearchParams() {
  const url = new URL(window.location.href);
  const password = url.searchParams.get("password");
  if (password !== null) {
    url.searchParams.delete("password");
    window.history.replaceState(null, "", url.toString());
  }
  return password;
}

function useAuth() {
  const PASSWORD_STORAGE_KEY = "@ticket-queue/password";
  const [password, setPassword] = useState(null);

  useEffect(() => {
    let checkedUrlParams = false;
    let urlPassword = null;

    if (!checkedUrlParams) {
      urlPassword = popPasswordFromSearchParams();
      if (urlPassword !== null) {
        setPassword(urlPassword);
      }
    }

    if (urlPassword === null) {
      const password = localStorage.getItem(PASSWORD_STORAGE_KEY);
      if (password === null) {
        console.debug("No password saved in localStorage");
      } else {
        console.debug("Found password in localStorage");
        setPassword(password);
      }
    }

    return () => {
      checkedUrlParams = true;
    };
  }, [setPassword]);

  useEffect(() => {
    if (password !== null) {
      console.log(
        `Setting password in ${PASSWORD_STORAGE_KEY} localStorage key`,
      );
      localStorage.setItem(PASSWORD_STORAGE_KEY, password);
    } else {
      console.log(
        `Removing password from ${PASSWORD_STORAGE_KEY} localStorage key`,
      );
      localStorage.removeItem(PASSWORD_STORAGE_KEY);
    }
  }, [password]);

  return [password, setPassword];
}

const AuthContext = createContext();

function useAuthContext() {
  const { password, setPassword } = useContext(AuthContext);
  if (password === null) {
    throw Error(
      "useAuthContext must be called inside an authenticated context",
    );
  }

  const logOut = useCallback(() => setPassword(null), [setPassword]);

  const fetchAdminWithAuth = useCallback(
    async (endpoint, payload = {}) => {
      return Api.fetchAdminApi(endpoint, password, payload).then((ret) => {
        if (ret.status === 401) {
          console.error("No longer authenticated!");
          logOut();
        } else {
          return ret;
        }
      });
    },
    [password, logOut],
  );

  const fetchAdminClientUrlWithAuth = useCallback(
    async (payload = {}) => {
      return Api.fetchAdminClientUrl(password, payload).then((ret) => {
        if (ret.status === 401) {
          console.error("No longer authenticated!");
          logOut();
        } else {
          return ret;
        }
      });
    },
    [password, logOut],
  );

  const fetchAdminAnnouncementWithAuth = useCallback(
    async (payload = {}) => {
      return Api.fetchAdminAnnouncement(password, payload).then((ret) => {
        if (ret.status === 401) {
          console.error("No longer authenticated!");
          logOut();
        } else {
          return ret;
        }
      });
    },
    [password, logOut],
  );

  const updateAdminAnnouncementWithAuth = useCallback(
    async (message, payload = {}) => {
      return Api.updateAdminAnnouncement(message, password, payload).then(
        (ret) => {
          if (ret.status === 401) {
            console.error("No longer authenticated!");
            logOut();
          } else {
            return ret;
          }
        },
      );
    },
    [password, logOut],
  );

  const deleteAdminTicketWithAuth = useCallback(
    async (id, payload = {}) => {
      return Api.deleteAdminTicket(id, password, payload).then((ret) => {
        if (ret.status === 401) {
          console.error("No longer authenticated!");
          logOut();
        } else {
          return ret;
        }
      });
    },
    [password, logOut],
  );

  return {
    password,
    logOut,
    fetchAdminWithAuth,
    fetchAdminClientUrlWithAuth,
    fetchAdminAnnouncementWithAuth,
    updateAdminAnnouncementWithAuth,
    deleteAdminTicketWithAuth,
  };
}

function TicketListItem({ ticket, onRemoveTicket, isDeleting }) {
  const waitTime = waitTimeMinutesString(ticket.timestamp);
  return (
    <li className="ticket-list-item">
      <div className="ticket-list-item-row">
        <div className="ticket-list-item-main">
          <span className="ticket-name">{ticket.name}</span>{" "}
          <span className="ticket-wait-time">({waitTime} min)</span>
        </div>
        <button
          className="button button--danger button--compact button--hover-reveal admin-remove-ticket-button"
          onClick={() => onRemoveTicket(ticket.id)}
          disabled={isDeleting}
          type="button"
        >
          {isDeleting ? "Removing..." : "Remove"}
        </button>
      </div>
    </li>
  );
}

function TicketsList({ tickets, onRemoveTicket, deletingTicketIds }) {
  return (
    <ol className="tickets-list">
      {tickets.map((ticket) => (
        <TicketListItem
          key={ticket.token}
          ticket={ticket}
          onRemoveTicket={onRemoveTicket}
          isDeleting={Boolean(deletingTicketIds[ticket.id])}
        />
      ))}
    </ol>
  );
}

function TicketsManager() {
  const { fetchAdminWithAuth, deleteAdminTicketWithAuth } = useAuthContext();
  const [tickets, setTickets] = useState(null);
  const [getTicketsError, setGetTicketsError] = useState(null);
  const [deleteTicketError, setDeleteTicketError] = useState(null);
  const [deletingTicketIds, setDeletingTicketIds] = useState({});

  useEffect(() => {
    const abortController = new AbortController();
    const signal = abortController.signal;

    function fetchTickets() {
      fetchAdminWithAuth("tickets", { signal })
        .then((ret) => {
          if (ret.ok) {
            return ret.json();
          }

          const error = "Error getting tickets";
          console.error(error);
          setGetTicketsError(error);
        })
        .then((tickets) => {
          setTickets(tickets);
          setGetTicketsError(null);
        });
    }

    console.debug("Fetching tickets...");
    fetchTickets();
    const id = setInterval(fetchTickets, 1000);
    return () => {
      clearInterval(id);
      abortController.abort("Cleanup");
    };
  }, [fetchAdminWithAuth, setGetTicketsError, setTickets]);

  useEffect(() => {
    if (tickets) {
      document.title = `(${tickets.length}) Ticket queue`;
    } else {
      document.title = "Ticket queue";
    }
    return () => {
      document.title = "Ticket queue";
    };
  }, [tickets]);

  function removeTicket(id) {
    if (deletingTicketIds[id]) {
      return;
    }

    setDeleteTicketError(null);
    setDeletingTicketIds((prev) => ({ ...prev, [id]: true }));
    deleteAdminTicketWithAuth(id)
      .then((ret) => {
        if (ret && ret.ok) {
          setTickets((prev) =>
            prev
              ? prev
                  .filter((ticket) => ticket.id !== id)
                  .map((ticket, index) => ({ ...ticket, position: index }))
              : prev,
          );
          return;
        }

        if (ret) {
          setDeleteTicketError("Error removing ticket");
        }
      })
      .catch(() => {
        setDeleteTicketError("Error removing ticket");
      })
      .finally(() => {
        setDeletingTicketIds((prev) => {
          const next = { ...prev };
          delete next[id];
          return next;
        });
      });
  }

  return getTicketsError ? (
    <p>Error getting tickets!</p>
  ) : !tickets || tickets.length === 0 ? (
    <p>No tickets</p>
  ) : (
    <>
      {deleteTicketError && (
        <p className="admin-remove-ticket-error">{deleteTicketError}</p>
      )}
      <TicketsList
        tickets={tickets}
        onRemoveTicket={removeTicket}
        deletingTicketIds={deletingTicketIds}
      />
    </>
  );
}

function ClientUrlManager() {
  const { fetchAdminClientUrlWithAuth } = useAuthContext();
  const [clientUrl, setClientUrl] = useState(null);
  const [clientUrlError, setClientUrlError] = useState(null);
  const [loadingClientUrl, setLoadingClientUrl] = useState(true);
  const [qrCodeDataUrl, setQrCodeDataUrl] = useState(null);

  useEffect(() => {
    const abortController = new AbortController();
    const signal = abortController.signal;

    fetchAdminClientUrlWithAuth({ signal })
      .then((ret) => {
        if (ret && ret.ok) {
          return ret.json();
        }
        if (ret) {
          setClientUrlError("Error getting client URL");
        }
      })
      .then((data) => {
        if (data && data.url) {
          setClientUrl(data.url);
          setClientUrlError(null);
        }
        setLoadingClientUrl(false);
      });

    return () => {
      abortController.abort("Cleanup");
    };
  }, [fetchAdminClientUrlWithAuth]);

  useEffect(() => {
    if (!clientUrl) {
      setQrCodeDataUrl(null);
      return;
    }

    QRCode.toDataURL(clientUrl, {
      margin: 1,
      width: 220,
    })
      .then((dataUrl) => setQrCodeDataUrl(dataUrl))
      .catch(() => setClientUrlError("Error generating QR code"));
  }, [clientUrl]);

  return (
    <div className="admin-client-url">
      {loadingClientUrl ? (
        <p>Loading URL...</p>
      ) : clientUrlError ? (
        <p className="admin-client-url-error">{clientUrlError}</p>
      ) : (
        <>
          <a href={clientUrl} target="_blank" rel="noreferrer">
            {clientUrl}
          </a>
          {qrCodeDataUrl && (
            <img
              className="admin-client-url-qrcode"
              src={qrCodeDataUrl}
              alt="QR code for ticket client URL"
            />
          )}
        </>
      )}
    </div>
  );
}

function AnnouncementManager() {
  const { fetchAdminAnnouncementWithAuth, updateAdminAnnouncementWithAuth } =
    useAuthContext();
  const [announcement, setAnnouncement] = useState(null);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const abortController = new AbortController();
    const signal = abortController.signal;

    fetchAdminAnnouncementWithAuth({ signal })
      .then((ret) => {
        if (!ret) {
          return null;
        }
        if (ret.ok) {
          return ret.json();
        }
        setError("Error loading announcement");
        return null;
      })
      .then((data) => {
        const message = data?.message || "";
        setAnnouncement(message);
        setDraft(message);
      })
      .finally(() => {
        setLoading(false);
      });

    return () => {
      abortController.abort("Cleanup");
    };
  }, [fetchAdminAnnouncementWithAuth]);

  function saveAnnouncement() {
    setSaving(true);
    setSaved(false);
    setError(null);
    updateAdminAnnouncementWithAuth(draft)
      .then((ret) => {
        if (!ret) {
          return null;
        }
        if (ret.ok) {
          return ret.json();
        }
        setError("Error saving announcement");
        return null;
      })
      .then((data) => {
        const message = data?.message || "";
        setAnnouncement(message);
        setDraft(message);
        setSaved(true);
      })
      .finally(() => {
        setSaving(false);
      });
  }

  if (loading) {
    return <p>Loading announcement...</p>;
  }

  return (
    <div className="announcement-manager">
      <p className="announcement-manager-label">Announcement message</p>
      <textarea
        className="announcement-manager-input"
        value={draft}
        onChange={(e) => {
          setDraft(e.target.value);
          setSaved(false);
        }}
        placeholder="Enter message shown to admins and ticket creators"
        rows={4}
      />
      <button
        className="button button--primary announcement-manager-save"
        onClick={saveAnnouncement}
        type="button"
        disabled={saving}
      >
        {saving ? "Saving..." : "Save message"}
      </button>
      {saved && <p className="announcement-manager-saved">Saved.</p>}
      {error && <p className="announcement-manager-error">{error}</p>}
      {announcement && (
        <div className="announcement-preview">
          <p className="announcement-preview-label">Current message</p>
          <p>{announcement}</p>
        </div>
      )}
    </div>
  );
}

function AdminDashboard() {
  const { logOut } = useAuthContext();
  return (
    <div className="admin-dashboard">
      <div className="admin-sidebar">
        <button
          className="button button--subtle button--compact admin-logout-button"
          onClick={logOut}
          type="button"
        >
          Log out
        </button>
        <AnnouncementManager />
        <ClientUrlManager />
      </div>
      <TicketsManager />
    </div>
  );
}

export default function Admin() {
  const [password, setPassword] = useAuth();
  return password === null ? (
    <PasswordEntry logIn={setPassword} />
  ) : (
    <AuthContext.Provider value={{ password, setPassword }}>
      <AdminDashboard />
    </AuthContext.Provider>
  );
}
