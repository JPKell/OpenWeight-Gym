# Security Policy

WeightRoomGym is the one component of the Local AI Suite built to face a network: it terminates TLS
with a certificate authority it mints for the operator, asks for a password, and then reads,
writes and restarts the four applications on the operator's behalf. Every other application keeps
its loopback bind behind it. The design is `docs/adr/0126-*.md` (exposure, TLS, login),
`docs/adr/0124-*.md` (the guard on writes into another application's database) and
`docs/apps/weightroom/spec.md` §14; `docs/security.md` is the operator's view once row W10
writes it.

## Reporting a vulnerability

Open a private security advisory on this repository, or contact the maintainer directly. Please
include the version, the deployment shape (loopback or LAN, SQLite or PostgreSQL) and a
reproduction. Do not open a public issue for a vulnerability.

In scope: this repository's own code and its documented configuration surface. Vulnerabilities in
the four applications, the operating system or a third-party dependency should be reported to that
project directly; `pip-audit` runs in this repository's CI to catch known vulnerable dependency
versions.
