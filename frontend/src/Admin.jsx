import { useEffect, useState } from "react";
import { fetchAdminApi } from "./api";

function useAdminPassword() {
  const PASSWORD_STORAGE_KEY = "@ticket-queue/password";
  const [password, setPassword] = useState(() =>
    localStorage.getItem(PASSWORD_STORAGE_KEY),
  );
  useEffect(() => {
    if (password) {
      localStorage.setItem(PASSWORD_STORAGE_KEY, password);
    } else {
      localStorage.removeItem(PASSWORD_STORAGE_KEY);
    }
  }, [password]);

  return [password, setPassword];
}

function LoggedIn() {
  return <p>Logged in!</p>;
}

function LogIn({ setPassword }) {
  const [passwordInput, setPasswordInput] = useState("");
  const [loginState, setLoginState] = useState("logged-out");

  function login() {
    setLoginState("logging-in");
    setPasswordInput("");
    fetchAdminApi("tickets", passwordInput).then((r) => {
      if (r.status == 200) {
        setPassword(passwordInput);
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
              login();
            }
          }}
          autoComplete="off"
        />
        <button disabled={!passwordInput} onClick={login}>
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

export default function Admin() {
  const [password, setPassword] = useAdminPassword();
  if (password) {
    return (
      <>
        <button onClick={() => setPassword(null)}>Log out</button>
        <LoggedIn password={password} />
      </>
    );
  }

  return <LogIn setPassword={setPassword} />;
}
