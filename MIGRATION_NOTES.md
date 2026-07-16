# CI Migration: Jenkins → GitHub Actions

This documents the migration of the fund-transfer-demo CI pipeline from a
self-hosted Jenkins server to GitHub Actions, stage by stage.

## Stage-by-stage mapping

| Jenkins stage                        | GitHub Actions equivalent                          | Notes |
|---------------------------------------|-----------------------------------------------------|-------|
| Declarative: Checkout SCM             | `actions/checkout@v4`                                | Built-in step, no config needed vs. Jenkins' Git plugin setup |
| Install Account Service Deps          | `build-and-test` job, `matrix.service = account-service` | Combined with the line below via a matrix, instead of two separate stages |
| Install Transfer Service Deps         | `build-and-test` job, `matrix.service = transfer-service` | Same job definition runs once per matrix value |
| Syntax Check                          | `Syntax check` step, per matrix entry                | `python -m py_compile app.py`, unchanged logic |
| Package                               | Separate `package` job, gated with `needs: build-and-test` | GitHub Actions jobs are isolated by default; `needs:` enforces the same ordering Jenkins gave for free within one pipeline |
| Verify Agent 1 (distributed build demo) | Dropped                                            | GitHub-hosted runners are provisioned fresh per job automatically — no manual agent registration needed, so there's nothing to demonstrate here |
| Install Test Deps / pytest run        | Not yet ported (known gap)                           | The integration test needs the full Docker Compose stack up and reachable over the network. Neither Jenkins nor this GitHub Actions workflow currently do that — it needs a later pipeline stage that starts the stack first (e.g., `docker compose up -d` before running `pytest`) |

## Why the matrix approach instead of duplicating steps

Jenkins' Jenkinsfile had two near-identical stages (one per service) because writing
each stage out was the natural syntax. GitHub Actions' `strategy.matrix` runs the
same set of steps once per value in a list, so both services are covered by one
job definition instead of two copy-pasted blocks. Fewer lines to keep in sync if
a step ever needs to change for both services.

## Environment differences encountered during migration

- **Jenkins** required manually installing Python, pip, and (for one dependency
  that needed to compile from source) a C compiler and PostgreSQL client headers,
  because the base `jenkins/jenkins:lts` image ships with nothing beyond Java and Git.
- **GitHub Actions** hosted runners come with Python pre-installed via
  `actions/setup-python@v5`, and the pinned dependency version used here
  (`psycopg2-binary==2.9.12`) has a pre-built wheel available, so no compiler
  toolchain was needed at all on this side.
- This is a real, measurable reduction in pipeline maintenance overhead — one of
  the stated reasons for migrating off Jenkins in the first place.

## Still open / not yet migrated

- Running the actual integration test (`pytest tests/`) against a live stack
- Docker image build + push to a registry
- Deployment stage (AWS / Kubernetes)