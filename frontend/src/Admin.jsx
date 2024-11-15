import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
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
            if (e.key === "Enter" && passwordInput) {
              tryLogIn();
            }
          }}
          autoComplete="off"
        />
        <button disabled={!passwordInput} onClick={tryLogIn}>
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

function useAuth() {
  const PASSWORD_STORAGE_KEY = "@ticket-queue/password";
  const [password, setPassword] = useState(() => {
    const password = localStorage.getItem(PASSWORD_STORAGE_KEY);
    if (password) {
      console.debug("Found password in localStorage");
    } else {
      console.debug("No password saved in localStorage");
    }
    return password;
  });
  useEffect(() => {
    if (password) {
      localStorage.setItem(PASSWORD_STORAGE_KEY, password);
    } else {
      localStorage.removeItem(PASSWORD_STORAGE_KEY);
    }
  }, [password]);

  return [password, setPassword];
}

const AuthContext = createContext();

function useAuthContext() {
  const { password, setPassword } = useContext(AuthContext);
  if (!password) {
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

  return { password, logOut, fetchAdminWithAuth };
}

function TicketListItem({ ticket }) {
  const waitTime = waitTimeMinutesString(ticket.timestamp);
  return (
    <li className="ticket-list-item">
      <span className="ticket-name">{ticket.name}</span>{" "}
      <span className="ticket-wait-time">({waitTime} min)</span>
    </li>
  );
}

function TicketsList({ tickets }) {
  return (
    <ul className="tickets-list">
      {tickets.map((ticket) => (
        <TicketListItem key={ticket.token} ticket={ticket} />
      ))}
    </ul>
  );
}

function TicketsManager() {
  const { fetchAdminWithAuth } = useAuthContext();
  const [tickets, setTickets] = useState(null);
  const [getTicketsError, setGetTicketsError] = useState(null);

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
      abortController.abort();
    };
  }, [fetchAdminWithAuth, setGetTicketsError, setTickets]);

  if (getTicketsError) {
    return <p>Error getting tickets!</p>;
  }

  if (!tickets || tickets.length === 0) {
    return <p>No tickets</p>;
  }

  return <TicketsList tickets={tickets} />;
}

function AdminDashboard() {
  const { logOut } = useAuthContext();
  return (
    <>
      <button onClick={logOut}>Log out</button>
      <TicketsManager />
    </>
  );
}

export default function Admin() {
  const [password, setPassword] = useAuth();
  return password ? (
    <AuthContext.Provider value={{ password, setPassword }}>
      <AdminDashboard />
    </AuthContext.Provider>
  ) : (
    <PasswordEntry logIn={setPassword} />
  );
}
