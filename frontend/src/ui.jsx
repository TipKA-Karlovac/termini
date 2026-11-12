import { useEffect, useRef } from "react";

export function Loading({ children = "Učitavam…" }) {
  return (
    <p className="muted" role="status">
      {children}
    </p>
  );
}

export function ErrorMessage({ children }) {
  if (!children) return null;
  return (
    <p className="alert alert-error" role="alert">
      {children}
    </p>
  );
}

/** Potvrda prije radnje koja se ne može poništiti. */
export function ConfirmDialog({ open, title, children, confirmLabel, busy, onConfirm, onClose }) {
  const ref = useRef(null);

  useEffect(() => {
    const dialog = ref.current;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog ref={ref} className="dialog" onClose={onClose} aria-labelledby="dialog-title">
      <h2 id="dialog-title">{title}</h2>
      <div className="dialog-body">{children}</div>
      <div className="actions">
        <button type="button" className="button button-quiet" onClick={onClose} disabled={busy}>
          Odustani
        </button>
        <button type="button" className="button button-danger" onClick={onConfirm} disabled={busy}>
          {busy ? "Otkazujem…" : confirmLabel}
        </button>
      </div>
    </dialog>
  );
}
