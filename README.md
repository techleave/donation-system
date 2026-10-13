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
- One tree costs 1,000 points. Atomic transactions and operation identifiers prevent double credits/debits on retries.
- Revision checks protect concurrent profile/CMS edits. Input validation, prepared SQL, same-origin write checks, HttpOnly cookies and session revocation protect data access.
- An admin can create/reset a donor login from the donor profile; the temporary password is displayed once. Email delivery and the existing password/PIN screen remain unimplemented, as requested for the earlier UI preview.

The original ChatGPT-hosted site's donors, uploaded images, requests and saved CMS edits have **not** been exported into Railway. Only data created on this Railway system is available here. Import donor CSVs through Donors Management, and provision each donor's login there.

## Local development and verification

Install JDK 17+ and Maven 3.9+. Run `mvn -B package`, configure environment variables (see `.env.example`), then run `java -jar target/donation-system.jar`.

Run `python3 tests/integration.py` after building. The test starts a real JVM with an isolated temporary database, verifies compatibility with the previous Node database/password format, checks permissions, CSV, photos/covers, CMS publishing, retry/concurrency protection, request history, account reset and persistence across a JVM restart. It does not access production data.
