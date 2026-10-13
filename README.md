# donate system demo — Railway edition

This package is an independent Railway adaptation of the existing donor rewards website. It retains the donor/admin layouts, bilingual text, covers, profiles, CSV import, private photos, request forms, administrator point additions, dated point history and 1,000-point tree redemption.

## Runtime

- Node.js 24, no npm dependencies or framework build required.
- SQLite database and uploaded images live in `DATA_DIR` on a persistent Railway volume.
- Email/password login, hashed passwords, HttpOnly sessions, server-side administrator and donor permissions.
- An administrator creates/resets each donor's login from Donors Management. The generated password is shown once; no email is sent automatically.
- Change Password / email PIN remains a visual demonstration, matching the previous scope. This is not an email verification or automated password recovery service.

## Deploy to Railway

1. Put the contents of this directory at the root of a GitHub repository.
2. Connect that repository to the `donate-system-demo` service in the already-created `donate system demo` Railway project.
3. Use the supplied Dockerfile and railway.json. Run one replica only.
4. Mount a persistent Railway volume at `/data`. Never use temporary container storage for production records.
5. Set `DATA_DIR=/data`, `NODE_ENV=production`, `PORT=8080`, `ADMIN_EMAIL`, and a unique `INITIAL_ADMIN_PASSWORD` of at least 12 characters. Do not commit real secrets.
6. Generate a domain and set `PUBLIC_URL` to its complete HTTPS origin (no trailing path).
7. Confirm `/health` returns status ok, then sign in at `/admin` using the configured administrator email/password.

`INITIAL_ADMIN_PASSWORD` is only used when there is no administrator account in the database. It does not reset an existing administrator's password on redeploy. Keep the configured administrator email stable. A previously provisioned donor logs in with the current donor-profile email; editing that email changes their login name as well.

## Local verification

Use a temporary directory and disposable credentials:

```
DATA_DIR=./data ADMIN_EMAIL=admin@example.com INITIAL_ADMIN_PASSWORD=your-unique-test-password node server.ts
node --test tests/*.test.ts
```

Tests use an isolated temporary database and cover authentication, spoofed identity rejection, administrator/donor separation, profile-backed submissions, point addition idempotency, tree debit idempotency, insufficient balance, CSV preview/import, photo privacy, transaction rollback and persisted data.

## Existing website data

This package contains application code, default content, static logos and artwork. It does **not** contain the original hosted D1 donor records, requests, point history, uploaded covers/photos, or saved admin draft/published settings. Those are still on the existing site. Do not describe this package as a complete live-data migration or switch the original link until those records have been exported and imported separately. Keep the original site online while completing the migration. Accounts use new Railway passwords; ChatGPT login and sessions cannot be transferred.

Existing SQL migrations are applied once on startup and tracked in `runtime_migrations`. Applied migration files must not be edited.

## Resource identity

Railway project: c752a01e-f99a-47f8-a101-5a616f000ef7
Environment: 41dd874a-d00e-4bb4-8cdc-c11eff1390a7
Source snapshot: aeaf343cfbd1fb570638d05482dcd53c67bbc9e6

The original Sites deployment and source have not been modified by this adaptation.
