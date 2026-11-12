import { cloneElement, useEffect, useRef, useState } from "react";
import { useOutletContext } from "react-router-dom";

import { api } from "../api.js";
import {
  dayOf,
  daysBetween,
  formatDayMonth,
  formatLongDay,
  formatPrice,
  formatTime,
  formatWeekday,
  splitByNoon,
} from "../dates.js";
import { ErrorMessage, Loading } from "../ui.jsx";

const EMPTY_FORM = { customer_name: "", customer_phone: "", customer_email: "", note: "" };

export default function Booking() {
  const config = useOutletContext();
  const [services, setServices] = useState(null);
  const [loadError, setLoadError] = useState("");
  const [service, setService] = useState(null);
  const [day, setDay] = useState(config.today);
  const [slot, setSlot] = useState(null);
  const [slotsVersion, setSlotsVersion] = useState(0);
  const [notice, setNotice] = useState("");
  const [booked, setBooked] = useState(null);

  useEffect(() => {
    const controller = new AbortController();
    api("/services/", { signal: controller.signal })
      .then(setServices)
      .catch((err) => {
        if (err.name !== "AbortError") setLoadError(err.message);
      });
    return () => controller.abort();
  }, []);

  if (booked) {
    return (
      <Confirmation
        appointment={booked}
        config={config}
        onAgain={() => {
          setBooked(null);
          setSlot(null);
          setSlotsVersion((version) => version + 1);
        }}
      />
    );
  }
  if (loadError) return <ErrorMessage>{loadError}</ErrorMessage>;
  if (!services) return <Loading />;
  if (services.length === 0) {
    return <p className="muted">Trenutno nema usluga koje se mogu rezervirati.</p>;
  }

  function chooseService(next) {
    setService(next);
    setSlot(null);
    setNotice("");
  }

  function chooseDay(next) {
    setDay(next);
    setSlot(null);
    setNotice("");
  }

  // Termin je u međuvremenu zauzet: makni odabir i ponovno dohvati slobodne.
  function slotTaken(message) {
    setSlot(null);
    setNotice(message);
    setSlotsVersion((version) => version + 1);
  }

  return (
    <>
      <Step number={1} title="Odaberite uslugu">
        <ul className="services">
          {services.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                className="service"
                aria-pressed={service?.id === item.id}
                onClick={() => chooseService(item)}
              >
                <span className="service-name">{item.name}</span>
                {item.description && <span className="service-text">{item.description}</span>}
                <span className="service-meta">
                  {item.duration_minutes} min · {formatPrice(item.price)}
                </span>
              </button>
            </li>
          ))}
        </ul>
      </Step>

      {service && (
        <Step number={2} title="Odaberite dan i vrijeme">
          <DayPicker config={config} day={day} onChange={chooseDay} />
          <ErrorMessage>{notice}</ErrorMessage>
          <Slots
            key={`${service.id}-${day}-${slotsVersion}`}
            service={service}
            day={day}
            timeZone={config.time_zone}
            selected={slot}
            onSelect={(next) => {
              setSlot(next);
              setNotice("");
            }}
          />
        </Step>
      )}

      {service && slot && (
        <Step number={3} title="Vaši podaci">
          <CustomerForm
            service={service}
            slot={slot}
            day={day}
            config={config}
            onBooked={setBooked}
            onSlotTaken={slotTaken}
          />
        </Step>
      )}
    </>
  );
}

function Step({ number, title, children }) {
  return (
    <section className="step" aria-labelledby={`step-${number}`}>
      <h2 id={`step-${number}`}>
        <span className="step-number">{number}</span>
        {title}
      </h2>
      {children}
    </section>
  );
}

function DayPicker({ config, day, onChange }) {
  const days = daysBetween(config.today, config.last_bookable_day);
  return (
    <div className="days" role="group" aria-label="Dan">
      {days.map((item) => (
        <button
          key={item}
          type="button"
          className="day"
          aria-pressed={item === day}
          aria-label={formatLongDay(item)}
          onClick={() => onChange(item)}
        >
          <span className="day-name">{item === config.today ? "danas" : formatWeekday(item)}</span>
          <span className="day-date">{formatDayMonth(item)}</span>
        </button>
      ))}
    </div>
  );
}

function Slots({ service, day, timeZone, selected, onSelect }) {
  const [slots, setSlots] = useState(null);
  const [error, setError] = useState("");

  // Komponenta dobiva novi `key` kad se promijeni usluga ili dan, pa uvijek
  // kreće od praznog stanja i dohvaća jednom.
  useEffect(() => {
    const controller = new AbortController();
    api(`/slots/?service=${service.id}&date=${day}`, { signal: controller.signal })
      .then((data) => setSlots(data.slots))
      .catch((err) => {
        if (err.name !== "AbortError") setError(err.message);
      });
    return () => controller.abort();
  }, [service.id, day]);

  if (error) return <ErrorMessage>{error}</ErrorMessage>;
  if (!slots) return <Loading>Tražim slobodne termine…</Loading>;
  if (slots.length === 0) {
    return (
      <p className="muted">
        Za {formatLongDay(day)} nema slobodnih termina. Odaberite drugi dan.
      </p>
    );
  }

  const { morning, afternoon } = splitByNoon(slots, timeZone);
  return (
    <div className="slot-groups">
      <SlotGroup title="Prijepodne" slots={morning} {...{ timeZone, selected, onSelect }} />
      <SlotGroup title="Poslijepodne" slots={afternoon} {...{ timeZone, selected, onSelect }} />
    </div>
  );
}

function SlotGroup({ title, slots, timeZone, selected, onSelect }) {
  if (slots.length === 0) return null;
  return (
    <div>
      <h3>{title}</h3>
      <div className="slots" role="group" aria-label={title}>
        {slots.map((slot) => (
          <button
            key={slot}
            type="button"
            className="slot"
            aria-pressed={slot === selected}
            onClick={() => onSelect(slot)}
          >
            {formatTime(slot, timeZone)}
          </button>
        ))}
      </div>
    </div>
  );
}

function validate(form) {
  const errors = {};
  if (form.customer_name.trim().length < 2) errors.customer_name = "Upišite ime i prezime.";
  if (!/^\+?[0-9][0-9 /()-]{5,28}$/.test(form.customer_phone.trim())) {
    errors.customer_phone = "Upišite telefonski broj, npr. 091 234 5678.";
  }
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.customer_email.trim())) {
    errors.customer_email = "Upišite adresu e-pošte, npr. ime@primjer.hr.";
  }
  return errors;
}

function CustomerForm({ service, slot, day, config, onBooked, onSlotTaken }) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [errors, setErrors] = useState({});
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const section = useRef(null);

  // Obrazac se pojavi ispod termina; na mobitelu bi inače ostao izvan zaslona.
  useEffect(() => {
    section.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [slot]);

  function change(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
    setErrors((current) => ({ ...current, [name]: undefined }));
  }

  function submit(event) {
    event.preventDefault();
    const found = validate(form);
    setErrors(found);
    setError("");
    if (Object.keys(found).length) return;

    setSubmitting(true);
    api("/appointments/", {
      method: "POST",
      body: {
        service: service.id,
        starts_at: slot,
        customer_name: form.customer_name.trim(),
        customer_phone: form.customer_phone.trim(),
        customer_email: form.customer_email.trim(),
        note: form.note.trim(),
      },
    })
      .then((appointment) => onBooked({ ...appointment, customer_email: form.customer_email.trim() }))
      .catch((err) => {
        setSubmitting(false);
        if (err.status === 409) onSlotTaken(err.message);
        else setError(err.message);
      });
  }

  return (
    <form ref={section} className="form" onSubmit={submit} noValidate>
      <p className="summary">
        <strong>{service.name}</strong> · {formatLongDay(day)} u{" "}
        <strong>{formatTime(slot, config.time_zone)}</strong>
      </p>

      <Field label="Ime i prezime" name="customer_name" error={errors.customer_name}>
        <input
          name="customer_name"
          value={form.customer_name}
          onChange={change}
          autoComplete="name"
          maxLength={80}
        />
      </Field>
      <Field label="Telefon" name="customer_phone" error={errors.customer_phone}>
        <input
          name="customer_phone"
          type="tel"
          value={form.customer_phone}
          onChange={change}
          autoComplete="tel"
          maxLength={30}
        />
      </Field>
      <Field
        label="E-pošta"
        name="customer_email"
        error={errors.customer_email}
        hint="Na ovu adresu šaljemo potvrdu i poveznicu za otkazivanje."
      >
        <input
          name="customer_email"
          type="email"
          value={form.customer_email}
          onChange={change}
          autoComplete="email"
          maxLength={254}
        />
      </Field>
      <Field label="Napomena (nije obavezno)" name="note">
        <textarea name="note" value={form.note} onChange={change} rows={3} maxLength={300} />
      </Field>

      <ErrorMessage>{error}</ErrorMessage>
      <button type="submit" className="button button-primary" disabled={submitting}>
        {submitting ? "Rezerviram…" : "Rezerviraj termin"}
      </button>
    </form>
  );
}

function Field({ label, name, error, hint, children }) {
  const describedBy = [hint && `${name}-hint`, error && `${name}-error`].filter(Boolean).join(" ");
  return (
    <div className="field">
      <label htmlFor={name}>{label}</label>
      {/* Jedino dijete je input ili textarea; dodajemo mu id i opis za čitače zaslona. */}
      {cloneElement(children, {
        id: name,
        "aria-invalid": error ? "true" : undefined,
        "aria-describedby": describedBy || undefined,
      })}
      {hint && (
        <p className="hint" id={`${name}-hint`}>
          {hint}
        </p>
      )}
      {error && (
        <p className="field-error" id={`${name}-error`} role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

function Confirmation({ appointment, config, onAgain }) {
  return (
    <section className="step" aria-labelledby="done-title">
      <h2 id="done-title">Termin je rezerviran</h2>
      <dl className="details">
        <dt>Usluga</dt>
        <dd>{appointment.service}</dd>
        <dt>Vrijeme</dt>
        <dd>
          {formatLongDay(dayOf(appointment.starts_at, config.time_zone))} u{" "}
          {formatTime(appointment.starts_at, config.time_zone)}
        </dd>
        <dt>Trajanje</dt>
        <dd>{appointment.duration_minutes} min</dd>
        <dt>Cijena</dt>
        <dd>{formatPrice(appointment.price)}</dd>
      </dl>
      <p>
        Potvrdu smo poslali na <strong>{appointment.customer_email}</strong>. U njoj je poveznica
        kojom termin možete otkazati najkasnije {config.cancel_until_hours} h prije početka.
      </p>
      <button type="button" className="button button-quiet" onClick={onAgain}>
        Rezerviraj još jedan termin
      </button>
    </section>
  );
}
