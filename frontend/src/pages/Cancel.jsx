import { useEffect, useState } from "react";
import { Link, useOutletContext, useParams } from "react-router-dom";

import { api } from "../api.js";
import { dayOf, formatLongDay, formatTime } from "../dates.js";
import { ConfirmDialog, ErrorMessage, Loading } from "../ui.jsx";

/** Stranica na koju vodi poveznica iz e-pošte: pregled termina i otkazivanje. */
export default function Cancel() {
  const config = useOutletContext();
  const { token } = useParams();
  const [appointment, setAppointment] = useState(null);
  const [loadError, setLoadError] = useState("");
  const [error, setError] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);

  const url = `/appointments/cancel/${encodeURIComponent(token)}/`;

  useEffect(() => {
    const controller = new AbortController();
    api(url, { signal: controller.signal })
      .then(setAppointment)
      .catch((err) => {
        if (err.name === "AbortError") return;
        setLoadError(
          err.status === 404
            ? "Poveznica nije ispravna. Provjerite jeste li je kopirali cijelu."
            : err.message,
        );
      });
    return () => controller.abort();
  }, [url]);

  function cancel() {
    setBusy(true);
    setError("");
    api(url, { method: "POST" })
      .then(setAppointment)
      .catch((err) => setError(err.message))
      .finally(() => {
        setBusy(false);
        setConfirming(false);
      });
  }

  if (loadError) return <ErrorMessage>{loadError}</ErrorMessage>;
  if (!appointment) return <Loading />;

  const when = `${formatLongDay(dayOf(appointment.starts_at, config.time_zone))} u ${formatTime(
    appointment.starts_at,
    config.time_zone,
  )}`;
  const cancelled = appointment.status === "cancelled";

  return (
    <section className="step" aria-labelledby="cancel-title">
      <h2 id="cancel-title">{cancelled ? "Termin je otkazan" : "Vaš termin"}</h2>
      <dl className="details">
        <dt>Ime</dt>
        <dd>{appointment.customer_name}</dd>
        <dt>Usluga</dt>
        <dd>{appointment.service}</dd>
        <dt>Vrijeme</dt>
        <dd>{when}</dd>
      </dl>

      <ErrorMessage>{error}</ErrorMessage>

      {cancelled ? (
        <p>
          Termin više nije rezerviran. <Link to="/">Rezervirajte novi termin.</Link>
        </p>
      ) : appointment.can_cancel ? (
        <button type="button" className="button button-danger" onClick={() => setConfirming(true)}>
          Otkaži termin
        </button>
      ) : (
        <p className="alert">
          Termin se putem interneta može otkazati najkasnije {config.cancel_until_hours} h prije
          početka. Ako ne možete doći, molimo nazovite nas.
        </p>
      )}

      <ConfirmDialog
        open={confirming}
        title="Otkazati termin?"
        confirmLabel="Da, otkaži"
        busy={busy}
        onConfirm={cancel}
        onClose={() => setConfirming(false)}
      >
        <p>
          {appointment.service}, {when}. Otkazivanje se ne može poništiti – za novi termin treba
          napraviti novu rezervaciju.
        </p>
      </ConfirmDialog>
    </section>
  );
}
