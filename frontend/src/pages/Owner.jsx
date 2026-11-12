import { useCallback, useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";

import { api } from "../api.js";
import { addDays, capitalize, formatLongDay, formatTime } from "../dates.js";
import { ConfirmDialog, ErrorMessage, Loading } from "../ui.jsx";

/** Dio za vlasnika: prijava, pa pregled termina po danima. */
export default function Owner() {
  const [user, setUser] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    // Ovaj poziv usput postavlja CSRF kolačić potreban za prijavu.
    api("/auth/me/", { signal: controller.signal })
      .then(setUser)
      .catch((err) => {
        if (err.name !== "AbortError") setError(err.message);
      });
    return () => controller.abort();
  }, []);

  if (error) return <ErrorMessage>{error}</ErrorMessage>;
  if (!user) return <Loading />;
  if (!user.authenticated) return <Login onLogin={setUser} />;
  return <Day user={user} onLogout={setUser} />;
}

function Login({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function submit(event) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    api("/auth/login/", { method: "POST", body: { username, password } })
      .then(onLogin)
      .catch((err) => {
        setError(err.message);
        setSubmitting(false);
      });
  }

  return (
    <section className="step narrow" aria-labelledby="login-title">
      <h2 id="login-title">Prijava za vlasnika</h2>
      <form className="form" onSubmit={submit}>
        <div className="field">
          <label htmlFor="username">Korisničko ime</label>
          <input
            id="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            autoComplete="username"
            required
          />
        </div>
        <div className="field">
          <label htmlFor="password">Lozinka</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
            required
          />
        </div>
        <ErrorMessage>{error}</ErrorMessage>
        <button type="submit" className="button button-primary" disabled={submitting}>
          {submitting ? "Prijavljujem…" : "Prijava"}
        </button>
      </form>
    </section>
  );
}

function Day({ user, onLogout }) {
  const config = useOutletContext();
  const [day, setDay] = useState(config.today);
  const [appointments, setAppointments] = useState(null);
  const [error, setError] = useState("");
  const [toCancel, setToCancel] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(
    (signal) =>
      api(`/owner/appointments/?date=${day}`, { signal })
        .then((data) => {
          setAppointments(data);
          setError("");
        })
        .catch((err) => {
          if (err.name !== "AbortError") setError(err.message);
        }),
    [day],
  );

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal);
    return () => controller.abort();
  }, [load]);

  function go(next) {
    setAppointments(null);
    setDay(next);
  }

  function cancel() {
    setBusy(true);
    api(`/owner/appointments/${toCancel.id}/cancel/`, { method: "POST" })
      .then(() => load())
      .catch((err) => setError(err.message))
      .finally(() => {
        setBusy(false);
        setToCancel(null);
      });
  }

  function logout() {
    api("/auth/logout/", { method: "POST" })
      .then(onLogout)
      .catch((err) => setError(err.message));
  }

  const booked = appointments?.filter((item) => item.status === "booked") ?? [];

  return (
    <section className="step" aria-labelledby="day-title">
      <div className="toolbar">
        <h2 id="day-title">{capitalize(formatLongDay(day))}</h2>
        <span className="muted">
          {user.username} ·{" "}
          <button type="button" className="link" onClick={logout}>
            Odjava
          </button>
        </span>
      </div>

      <div className="actions actions-start">
        <button type="button" className="button button-quiet" onClick={() => go(addDays(day, -1))}>
          ← Prethodni dan
        </button>
        <button
          type="button"
          className="button button-quiet"
          onClick={() => go(config.today)}
          disabled={day === config.today}
        >
          Danas
        </button>
        <button type="button" className="button button-quiet" onClick={() => go(addDays(day, 1))}>
          Sljedeći dan →
        </button>
        <input
          type="date"
          className="date-input"
          aria-label="Odaberite datum"
          value={day}
          onChange={(event) => event.target.value && go(event.target.value)}
        />
      </div>

      <ErrorMessage>{error}</ErrorMessage>

      {!appointments ? (
        <Loading />
      ) : appointments.length === 0 ? (
        <p className="muted">Za ovaj dan nema termina.</p>
      ) : (
        <>
          <p className="muted">Rezervirano termina: {booked.length}</p>
          <ul className="appointments">
            {appointments.map((item) => (
              <li
                key={item.id}
                className={item.status === "cancelled" ? "appointment cancelled" : "appointment"}
              >
                <div className="appointment-time">
                  {formatTime(item.starts_at, config.time_zone)}–
                  {formatTime(item.ends_at, config.time_zone)}
                </div>
                <div className="appointment-body">
                  <strong>{item.customer_name}</strong>
                  <span>{item.service}</span>
                  <span>
                    <a href={`tel:${item.customer_phone.replace(/[^0-9+]/g, "")}`}>
                      {item.customer_phone}
                    </a>{" "}
                    · <a href={`mailto:${item.customer_email}`}>{item.customer_email}</a>
                  </span>
                  {item.note && <span className="note">„{item.note}”</span>}
                </div>
                <div className="appointment-actions">
                  {item.status === "cancelled" ? (
                    <span className="badge">otkazano</span>
                  ) : (
                    <button
                      type="button"
                      className="button button-quiet"
                      onClick={() => setToCancel(item)}
                    >
                      Otkaži
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </>
      )}

      <ConfirmDialog
        open={toCancel !== null}
        title="Otkazati termin?"
        confirmLabel="Da, otkaži"
        busy={busy}
        onConfirm={cancel}
        onClose={() => setToCancel(null)}
      >
        {toCancel && (
          <p>
            {toCancel.customer_name}, {toCancel.service} u{" "}
            {formatTime(toCancel.starts_at, config.time_zone)}. Klijent će dobiti obavijest
            e-poštom.
          </p>
        )}
      </ConfirmDialog>
    </section>
  );
}
