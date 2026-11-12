# termini

[![CI](https://github.com/TipKA-Karlovac/termini/actions/workflows/ci.yml/badge.svg)](https://github.com/TipKA-Karlovac/termini/actions/workflows/ci.yml)

Rezervacija termina putem interneta za male uslužne obrte – frizerske i
kozmetičke salone, servise, ordinacije. Klijent sam odabere uslugu i slobodan
termin, a vlasnik na jednom mjestu vidi tko dolazi i kada.

*English summary: online appointment booking for small service businesses.
Django REST API + React front end. Double bookings are prevented by a
PostgreSQL exclusion constraint, not only by application code.*

## Što radi

**Klijent** (bez registracije i prijave):

- odabere uslugu, dan i jedan od slobodnih termina
- upiše ime, telefon i e-poštu
- dobije potvrdu e-poštom s poveznicom za otkazivanje
- poveznicom može otkazati termin do 2 h prije početka

**Vlasnik** (uz prijavu):

- vidi termine po danima, s kontaktima klijenata
- može otkazati termin; klijent dobije obavijest e-poštom
- usluge, radno vrijeme i neradne dane uređuje u Djangovom adminu (`/admin/`)

Slobodni termini računaju se iz radnog vremena (može biti dvokratno), trajanja
usluge, neradnih dana i već rezerviranih termina. Sve se prikazuje u vremenu
salona (Europe/Zagreb), bez obzira na to gdje je klijentov preglednik, i
ispravno prelazi preko pomicanja sata.

## Kako se sprječava dvostruka rezervacija

Dva klijenta mogu u istoj sekundi poslati zahtjev za isti termin. Provjera u
kodu („je li termin slobodan?”) tada nije dovoljna, jer oba zahtjeva mogu
dobiti odgovor „jest” prije nego što ijedan upiše rezervaciju.

Zato postoje dvije obrane:

1. **U kodu** – termin se provjerava i upisuje unutar jedne transakcije
   ([`booking/services.py`](backend/booking/services.py)).
2. **U bazi** – na PostgreSQL-u isključujuće ograničenje zabranjuje dva
   rezervirana termina čija se vremena preklapaju
   ([migracija 0002](backend/booking/migrations/0002_appointment_no_overlap.py)):

   ```sql
   ALTER TABLE booking_appointment
   ADD CONSTRAINT booking_appointment_no_overlap
   EXCLUDE USING gist (tstzrange(starts_at, ends_at) WITH &&)
   WHERE (status = 'booked');
   ```

   Drugi upis baza odbije, a klijent dobije poruku da odabere drugi termin.

Lokalno, na SQLiteu, tog ograničenja nema; ondje istodobne upise sprječava
zaključavanje baze pri upisu. Test koji upisuje preklapanje izravno u bazu
izvršava se u CI-ju na PostgreSQL-u.

## Tehnologije

| Dio | Tehnologije |
|---|---|
| Backend | Python, Django 5.2, Django REST framework |
| Baza | PostgreSQL (produkcija), SQLite (razvoj) |
| Frontend | React 19, React Router, Vite |
| Kvaliteta | pytest, Vitest, Ruff, ESLint, GitHub Actions |

## Pokretanje na svom računalu

Potrebni su Python 3.11+ i Node 20+. Baza je SQLite, pa ništa drugo ne treba
instalirati.

**Backend** (Windows PowerShell):

```powershell
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
$env:DJANGO_DEBUG = "1"
.venv\Scripts\python manage.py migrate
.venv\Scripts\python manage.py seed_demo --owner vlasnik
.venv\Scripts\python manage.py changepassword vlasnik
.venv\Scripts\python manage.py runserver
```

Na Linuxu i macOS-u umjesto `.venv\Scripts\` pišite `.venv/bin/`, a varijablu
postavite s `export DJANGO_DEBUG=1`.

`seed_demo` upisuje primjer salona: četiri usluge i radno vrijeme
ponedjeljak–petak 8–12 i 14–18, subotom 8–13.

**Frontend** (u drugom prozoru):

```powershell
cd frontend
npm install
npm run dev
```

Aplikacija je na <http://localhost:5173>, dio za vlasnika na
<http://localhost:5173/vlasnik>. E-pošta se u razvoju ne šalje, nego se
ispisuje u prozoru u kojem radi backend – ondje je i poveznica za otkazivanje.

## Testovi

```powershell
cd backend
.venv\Scripts\python -m pytest
.venv\Scripts\python -m ruff check .

cd ..\frontend
npm test
npm run lint
```

Testovi backenda pokrivaju izračun slobodnih termina (dvokratno radno vrijeme,
preklapanja, rok najave, neradni dani, pomicanje sata), cijeli API, prijavu
vlasnika, CSRF zaštitu i ograničenje broja pokušaja.

## Postavke

Sve postavke dolaze iz varijabli okruženja; popis je u
[`backend/.env.example`](backend/.env.example). Najvažnije:

| Varijabla | Značenje | Zadano |
|---|---|---|
| `DJANGO_DEBUG` | razvojni način (SQLite, e-pošta u konzoli) | isključeno |
| `DJANGO_SECRET_KEY` | tajni ključ, obavezan izvan razvoja | – |
| `DATABASE_URL` | `postgres://korisnik:lozinka@host:port/baza` | SQLite |
| `FRONTEND_URL` | adresa web sučelja, za poveznice u e-pošti | `http://localhost:5173` |
| `BUSINESS_NAME` | naziv salona | Salon Primjer |
| `BOOKING_SLOT_STEP_MINUTES` | razmak između ponuđenih termina | 15 |
| `BOOKING_MIN_LEAD_MINUTES` | najmanje vrijeme od sada do termina | 60 |
| `BOOKING_MAX_DAYS_AHEAD` | koliko dana unaprijed se može rezervirati | 30 |
| `BOOKING_CANCEL_UNTIL_HOURS` | do koliko sati prije klijent može otkazati | 2 |

## API

| Metoda i adresa | Tko | Što radi |
|---|---|---|
| `GET /api/config/` | svi | naziv salona, vremenska zona, raspon dana |
| `GET /api/services/` | svi | aktivne usluge |
| `GET /api/slots/?service=1&date=2026-03-02` | svi | slobodni termini za dan |
| `POST /api/appointments/` | svi | rezervacija |
| `GET`/`POST /api/appointments/cancel/<token>/` | klijent s poveznicom | pregled i otkazivanje |
| `GET /api/auth/me/`, `POST /api/auth/login/`, `POST /api/auth/logout/` | vlasnik | prijava |
| `GET /api/owner/appointments/?date=2026-03-02` | vlasnik | termini dana s kontaktima |
| `POST /api/owner/appointments/<id>/cancel/` | vlasnik | otkazivanje |

Javne adrese ne otkrivaju ništa o tuđim rezervacijama: popis slobodnih termina
sadrži samo vremena, a odgovor na rezervaciju ne sadrži poveznicu za
otkazivanje – ona stiže isključivo e-poštom.

## Što (još) nije uključeno

- više djelatnika s odvojenim kalendarima – trenutno je jedan kalendar po salonu
- podsjetnik dan prije termina
- plaćanje unaprijed
- uređivanje usluga i radnog vremena izvan Djangovog admina
- upute za postavljanje na poslužitelj

## Licenca

[MIT](LICENSE)
