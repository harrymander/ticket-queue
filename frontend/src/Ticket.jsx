import { createContext, useContext, useEffect, useRef, useState } from "react";
import * as Api from "./api";
import { waitTimeMinutesString, ordinalString } from "./utils";

function useTicketStorage() {
  const TICKET_STORAGE_KEY = "@ticket-queue/ticket";

  const [ticket, setTicket] = useState(() => {
    const storedVal = localStorage.getItem(TICKET_STORAGE_KEY);
    if (!storedVal) {
      console.debug("No ticket in storage");
      return null;
    }

    try {
      const ticket = JSON.parse(storedVal);
      Api.validateTicket(ticket);
      console.debug("Ticket found in storage.", ticket);
      return ticket;
    } catch (error) {
      console.error("Invalid ticket in storage; clearing.", storedVal, error);
      return null;
    }
  });

  useEffect(() => {
    if (ticket) {
      localStorage.setItem(TICKET_STORAGE_KEY, JSON.stringify(ticket));
    } else {
      localStorage.removeItem(TICKET_STORAGE_KEY);
    }
  }, [ticket]);

  return [ticket, setTicket];
}

function useTicket() {
  const [ticket, setTicket] = useTicketStorage();
  const [ticketPending, setTicketPending] = useState(false);
  const [ticketError, setTicketError] = useState(null);
  const intervalRef = useRef();

  useEffect(() => {
    const abortController = new AbortController();
    const signal = abortController.signal;

    if (ticket) {
      intervalRef.current = setInterval(() => {
        Api.fetchTicket(ticket.id, ticket.token, { signal })
          .then((ret) => {
            if (ret.ok) {
              return ret.json();
            }

            // TODO: probably should be more specific with the errors we check
            // (e.g. 500 errors)
            console.info("Ticket not available on remote server, clearing");
            setTicket(null);
          })
          .then(setTicket);
      }, 1000);
      return () => {
        clearInterval(intervalRef.current);
        abortController.abort();
      };
    }
    clearInterval(intervalRef.current);
  }, [ticket, setTicket]);

  useEffect(() => {
    function resetTitle() {
      document.title = "Ticket queue";
    }

    if (ticket) {
      document.title = `(${ticket.position + 1}) Ticket queue`;
    } else {
      resetTitle();
    }
    return resetTitle;
  }, [ticket]);

  function createTicket(name) {
    if (ticket) {
      console.error("Ticket already exists!");
      return;
    }

    setTicketPending(true);
    setTicketError(null);
    Api.newTicket(name)
      .then((ret) => {
        setTicketPending(false);
        if (ret.ok) {
          return ret.json();
        }
        const error = "error creating ticket";
        console.error(error);
        setTicketError(error);
      })
      .then((ticket) => {
        console.info("New ticket", ticket);
        setTicket(ticket);
      });
  }

  function deleteTicket() {
    if (!ticket) {
      console.error("No ticket to delete!");
      return;
    }

    setTicketPending(true);
    setTicketError(null);
    Api.deleteTicket(ticket.id, ticket.token).then(() => {
      // TODO: at the moment we are just removing the ticket if fails...
      // maybe do something else depending on the return type (404 vs 401
      // etc.)
      setTicket(null);
      setTicketPending(false);
    });
  }

  return {
    ticket,
    ticketPending,
    ticketError,
    createTicket,
    deleteTicket,
  };
}

const TicketContext = createContext();

function useTicketContext() {
  const ticket = useContext(TicketContext);
  if (!ticket) {
    throw Error("useTicketContext must be called inside a TicketContext");
  }
  return ticket;
}

function TicketInfo({ ticket }) {
  return (
    <div className="ticket-info">
      <p className="ticket-name">{ticket.name}</p>
      <p className="ticket-position">
        You are{" "}
        <span className="ticket-position-ordinal">
          {ordinalString(ticket.position + 1)}
        </span>{" "}
        in the queue.
      </p>
      <p className="ticket-wait-time">
        You have been waiting for {waitTimeMinutesString(ticket.timestamp)} min.
      </p>
    </div>
  );
}

function HasTicket() {
  const { ticket, deleteTicket, ticketPending, ticketError } =
    useTicketContext();

  return (
    <>
      <TicketInfo ticket={ticket} />
      {ticketPending ? (
        <p>Deleting...</p>
      ) : (
        <button
          className="button button--danger"
          onClick={deleteTicket}
          type="button"
        >
          Leave queue
        </button>
      )}
      {ticketError && <p className="ticket-delete-error">{ticketError}</p>}
    </>
  );
}

function AnnouncementMessage() {
  const [announcement, setAnnouncement] = useState(null);
  const [announcementError, setAnnouncementError] = useState(null);

  useEffect(() => {
    const abortController = new AbortController();
    const signal = abortController.signal;

    Api.fetchAnnouncement({ signal })
      .then((ret) => {
        if (ret.ok) {
          return ret.json();
        }
        setAnnouncementError("Error loading message");
        return null;
      })
      .then((data) => {
        setAnnouncement(data?.message || null);
      });

    return () => {
      abortController.abort("Cleanup");
    };
  }, []);

  if (announcementError) {
    return <p className="announcement-error">{announcementError}</p>;
  }

  if (announcement) {
    return (
      <div className="announcement-message">
        <p>{announcement}</p>
      </div>
    );
  }

  return null;
}

function TicketCreator() {
  const { createTicket, ticketPending, ticketError } = useTicketContext();
  const [value, setValue] = useState("");
  const valueTrimmed = value.trim();

  if (ticketPending) {
    return <p>Creating ticket...</p>;
  }

  function submit() {
    if (valueTrimmed) {
      createTicket(valueTrimmed);
    }
  }

  return (
    <div className="create-ticket">
      <AnnouncementMessage />
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            submit();
          }
        }}
      />
      <button
        className="button button--primary"
        disabled={valueTrimmed === ""}
        onClick={submit}
        type="button"
      >
        Create
      </button>
      {ticketError && <p className="create-ticket-error">{ticketError}</p>}
    </div>
  );
}

function App() {
  const { ticket } = useTicketContext();
  return ticket ? <HasTicket /> : <TicketCreator />;
}

export default function Ticket() {
  const ticket = useTicket();
  return (
    <TicketContext.Provider value={ticket}>
      <App />
    </TicketContext.Provider>
  );
}
