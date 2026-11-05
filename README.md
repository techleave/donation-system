# donate system demo

Full donor rewards system with a **Java 17 backend**, a bilingual donor/admin website, HTTP APIs, authenticated sessions, a SQLite database, and persistent image storage. Source is maintained in `techleave/donation-system`; the JVM, database and uploaded images run on Railway.

## Architecture

- `src/main/java/org/hkvc/donate/Application.java`: HTTP controllers, donor profiles, CMS, rewards, CSV import, images and submission history.
- `Auth.java`: server-side admin/donor roles, scrypt password hashes, login rate limit and revocable sessions.
- `Store.java`: JDBC database, migrations, transactions and atomic uploaded-file writes.
- `Validation.java`: donor, reward, CMS and CSV input validation.
- `lib/portal.html` and `lib/admin.html`: browser views served by the Java application. HTML/JavaScript are the website interface, not the database or backend.
- `public/`: campaign images and logos.

The app **does not run Node.js**. Maven creates a single executable Java JAR, including the views and static assets. Docker builds and starts that JAR.

## Railway deployment

Project: `donate system demo` (`c752a01e-f99a-47f8-a101-5a616f000ef7`). Service: `donate-system-demo` (`18406847-ad2d-425e-9378-ab71e3d77384`). Production environment: `41dd874a-d00e-4bb4-8cdc-c11eff1390a7`.

GitHub source: `techleave/donation-system`, branch `main`. Start command: `java -XX:MaxRAMPercentage=70 -jar /app/donation-system.jar`. Healthcheck: `/health`.

Mount the persistent Railway volume at `/data`, set `DATA_DIR=/data`, and keep **one replica**. The database is `/data/donate.sqlite`, and uploaded images are `/data/objects`. Data survives restarts and code redeployments. This is a volume-backed SQLite database, not a separate PostgreSQL service. Do not remove the volume or database to update the website.

Required environment variables:

| Variable | Meaning |
| --- | --- |
| `PORT` | HTTP listening port, normally `8080` |
| `DATA_DIR` | Persistent data directory, `/data` on Railway |
| `PUBLIC_URL` | Exact public HTTPS origin, used for origin checks and secure cookies |
| `ADMIN_EMAIL` | Administrator email |
| `INITIAL_ADMIN_PASSWORD` | Strong initial password, at least 12 characters; used only if there is no existing admin |

Secrets belong in Railway variables; never commit `.env`, passwords or database files. Existing Railway SQLite tables, uploaded images, session tokens and scrypt passwords from the previous Node version are reused. Migrations are applied once; upgrading does not reset accounts or data.

## Features

- Donor sign-in, own profile, points ledger, four reward cards and persistent submission history. Users can see only their own profile, photos, points and requests.
- Admin interface, all donor/request management, CSV preview/import, PNG/JPG donor photos, dated point credits, cover images and editable/publishable bilingual website configuration.
- Each reward has its own donation-based allowance. Atomic transactions and operation identifiers prevent duplicate redemptions on retries.
- Revision checks protect concurrent profile/CMS edits. Input validation, prepared SQL, same-origin write checks, HttpOnly cookies and session revocation protect data access.
- An admin can create/reset a donor login from the donor profile; the temporary password is displayed once. Email delivery and the existing password/PIN screen remain unimplemented, as requested for the earlier UI preview.

The administrator-only `/api/admin/import-site-data` endpoint imports the original Sites donor profiles, point ledger and requests with original identifiers, timestamps and balances. It checks for conflicts, backs up the Railway database, imports in one transaction and records an idempotency receipt. A repeated identical snapshot is a no-op; a changed snapshot is rejected for review. Runtime data and backups stay on Railway and are never committed to GitHub. ChatGPT user identities cannot become independent email/password credentials: provision donor logins through Donors Management. The current published original-site configuration matches the bundled website configuration.

## Local development and verification

Install JDK 17+ and Maven 3.9+. Run `mvn -B package`, configure environment variables (see `.env.example`), then run `java -jar target/donation-system.jar`.

Run `python3 tests/integration.py` after building. The test starts a real JVM with an isolated temporary database, verifies compatibility with the previous Node database/password format, checks permissions, CSV, photos/covers, CMS publishing, retry/concurrency protection, request history, account reset and persistence across a JVM restart. It does not access production data.


## Donation allowances

Donations are recorded in HKD, to two decimal places. The displayed cumulative
points are `floor(cumulative HKD / 5000) * 1000`; they are not a shared spendable
balance. Airport lounge visits, melody cards and trees each earn one independent
allowance per HK$5,000. Tickets earn one allowance from HK$5,000 and two in total
from HK$50,000 (no further automatic ticket increases). Thresholds do not reset
monthly. Pending and completed requests both count as used; completion does not
consume another allowance. Every card request is one card, every airport/ticket
request one allowance, and tree quantity uses that many tree allowances.

Donors Management → Import CSV → CSV template includes:
`Prefix,English Full Name,Chinese Full Name,Phone,Email,Cumulative Donation,Donation Date`.
The donation column is the **cumulative total**, not a new monthly payment. Emails
match existing donors; photos, logins and request history stay linked. Equal
amounts do not create donations again. Lower snapshots are reported and skipped,
so an old file cannot reduce the total. A CSV without donation columns still
imports profile details only. Dates accept YYYY-MM-DD or DD/MM/YYYY. Use UTF-8;
quote amounts containing thousands separators. Import validates the entire file
before an atomic write and previews donation changes and skipped lower totals.

Click a donor's cumulative points to view all four earned/used/remaining counts,
donation dates, dated total changes and to record/correct the cumulative total.
Corrections require the current profile revision; reduced totals keep all
redemption history and clamp available allowances at zero. Submitted requests
are checked and recorded in one transaction; repeated request IDs cannot consume
another allowance, and concurrent requests cannot over-redeem.

On first startup after this update, the app creates a SQLite backup named
`before-donation-entitlements-*.sqlite` on the persistent volume, then introduces
separate donation accounting tables. Existing profiles, demo point ledgers and
requests are retained. Legacy demo points are **not converted into money**.
Historical requests linked to a donor count towards that donor's used allowances
(tree quantity is read from its saved fields; other legacy requests count as one).
Enter verified cumulative donation totals to activate donor allowances.
