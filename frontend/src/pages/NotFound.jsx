import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <section className="step">
      <h2>Stranica ne postoji</h2>
      <p>
        <Link to="/">Povratak na rezervaciju termina</Link>
      </p>
    </section>
  );
}
