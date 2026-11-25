# Data, Security and Compliance

- Market data: follow guide catalog; verify storage, use and redistribution licenses. Publish only synthetic or explicitly redistributable fixtures. Immutable raw data, versions and availability dates.
- Decision D001: shared code, dependency versions, schemas and synthetic tests are versioned; WRDS and other licensed datasets, local derived datasets, logs, saves and virtual environments remain local. CI must not require access to private datasets. Collaborators provision data independently under their own access rights.
- Financial profiles and behavioral responses: minimization, explicit consent, role-based access, identity/profile separation, encryption in transit and at rest, minimal logging, defined retention and applicable deletion rights. No personal data in Git, issues, notebooks or logs.
- Secrets: ignore local .env, use production secret manager; rotate after exposure. Never commit tokens or put them in CI.
- API: authentication, resource authorization, validation, rate limiting, cross-user access tests, backups and restoration.
- Models: version registry, constraint and drift audit, human review. No manipulative personalization based on presumed biases.
- Production: independent applicable legal assessment (privacy, product suitability and advisory obligations), security/model reviews before real service. Research MVP has no real orders.
- The current local save feature is simulation-only: separate encrypted payloads stored in the current browser, with a user-chosen four-digit PIN; older saves retain their original passphrase. A four-digit PIN has low entropy and is not strong protection against offline guessing. Save names are visible metadata; use fictional names and never real client information. No network transfer or password recovery. Browser storage is not a substitute for production authentication, security or a durable backup.
