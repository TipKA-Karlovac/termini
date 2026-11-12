// Tanki omotač oko fetcha: JSON, CSRF zaglavlje i pogreške s porukom za korisnika.

const FIELD_LABELS = {
  customer_name: "Ime i prezime",
  customer_phone: "Telefon",
  customer_email: "E-pošta",
  note: "Napomena",
  service: "Usluga",
  starts_at: "Termin",
  username: "Korisničko ime",
  password: "Lozinka",
};

export class ApiError extends Error {
  constructor(status, data) {
    super(describe(status, data));
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

function describe(status, data) {
  if (data && typeof data.detail === "string") return data.detail;
  if (status === 429) return "Previše pokušaja. Pričekajte malo pa pokušajte ponovno.";
  if (status === 400 && data && typeof data === "object") {
    const fields = Object.keys(data).map((name) => FIELD_LABELS[name] || name);
    if (fields.length) return `Provjerite unos: ${fields.join(", ")}.`;
  }
  if (status === 403) return "Pristup nije dopušten. Osvježite stranicu i prijavite se ponovno.";
  if (status === 404) return "Traženi podatak ne postoji.";
  return "Nešto je pošlo po zlu. Pokušajte ponovno.";
}

function csrfToken() {
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

export async function api(path, { method = "GET", body, signal } = {}) {
  const headers = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (method !== "GET") headers["X-CSRFToken"] = csrfToken();

  let response;
  try {
    response = await fetch(`/api${path}`, {
      method,
      headers,
      signal,
      credentials: "same-origin",
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new ApiError(0, { detail: "Nema veze s poslužiteljem. Provjerite internet." });
  }

  let data = null;
  try {
    data = await response.json();
  } catch {
    // Odgovor bez tijela ili tijelo koje nije JSON.
  }
  if (!response.ok) throw new ApiError(response.status, data);
  return data;
}
