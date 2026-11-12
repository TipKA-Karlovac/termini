import { useEffect, useState } from "react";
import { Link, Outlet } from "react-router-dom";

import { api } from "./api.js";
import { ErrorMessage, Loading } from "./ui.jsx";

/** Okvir svih stranica. Jednom dohvaća postavke salona i daje ih stranicama. */
export default function Layout() {
  const [config, setConfig] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    api("/config/", { signal: controller.signal })
      .then((data) => {
        setConfig(data);
        document.title = `Rezervacija termina – ${data.business_name}`;
      })
      .catch((err) => {
        if (err.name !== "AbortError") setError(err.message);
      });
    return () => controller.abort();
  }, []);

  return (
    <div className="page">
      <header className="header">
        <Link to="/" className="brand">
          {config ? config.business_name : " "}
        </Link>
        <span className="tagline">Rezervacija termina</span>
      </header>

      <main className="main">
        {error ? (
          <ErrorMessage>{error}</ErrorMessage>
        ) : config ? (
          <Outlet context={config} />
        ) : (
          <Loading />
        )}
      </main>

      <footer className="footer">
        <Link to="/vlasnik">Prijava za vlasnika</Link>
      </footer>
    </div>
  );
}
