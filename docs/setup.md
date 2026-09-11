# Setting up WeightRoomGym

The wizard end to end, what it leaves on the host, and the per-device trust step. Written at row
W10 for `wr-gym 1.0.0`; the LAN shape it installs is
[ADR-0126](adr/0126-weightroom-is-the-only-service-on-the-lan-and-terminates-tls-with-its-own-ca.md)
and the process shape is
[ADR-0125](adr/0125-weightroom-drives-the-applications-through-systemd-user-units-it-writes.md).

## 1. Before you start

* **Linux with `systemd --user`** for process control (Debian, Ubuntu, Fedora, Arch). Without it
  every page still serves; the process pages say *unsupported on this host* by name
  (spec §16).
* **Python 3.12 or newer**, and the four applications installed in their own virtualenvs if you
  want to run them — `wr-gym` never installs them (ADR-0123 rule 3). Each one's CLI must be
  reachable: on `PATH`, or named per application in `[apps.<name>] executable`.
* **Ollama** running as `ollama.service` if any application uses it, under the memory cap
  [`MEMORY_SAFETY.md`](MEMORY_SAFETY.md) §2.1 describes; `wr-gym doctor` checks the cap lines
  and prints `docs/scripts/apply_memory_safety.sh` when they are missing.
* The host's own name resolves on the LAN (`<hostname>.local` through mDNS, or a DNS entry).
  The certificate names the hostname, `<hostname>.local`, every LAN address and `localhost`.

```bash
pipx install wr-gym          # or: python -m venv ~/wr && ~/wr/bin/pip install wr-gym
wr-gym --version             # wr-gym 1.0.0 (api v1)
```

## 2. The wizard

```bash
wr-gym setup
```

Every prompt has a flag (`wr-gym setup --help`): `--username`, `--password-stdin` for scripts,
`--bind loopback|lan|all`, `--lan-address <interface address>`, `--no-start-console`. The steps,
in order, each printed as it lands:

| Step | What it does | Where it lands |
|---|---|---|
| `host` | Reads the hostname and the LAN addresses | the certificate's names and `allowed_hosts` |
| `tls` | Creates the certificate authority (ECDSA P-256, ten years) and the server certificate (398 days, renewed automatically inside 30 days of expiry) | `~/.config/wr-gym/tls/{ca,server}.{key,crt}` (`0600` keys) |
| `account` | Creates the one operator account; the password is scrypt-hashed and never written | the `operators` table |
| `bind` | `server.host` — loopback, one LAN interface, or `0.0.0.0` with `allow_lan_exposure` | `~/.config/wr-gym/config.toml` |
| `hosts` | `server.allowed_hosts` — the hostname, `<hostname>.local`, the LAN addresses | `config.toml` |
| `token` | A `write` token on LoadCoach and a `write,approve` token on PromptCadence, for chat; only for an application that is installed | `~/.config/wr-gym/secrets/<app>.token` (`0600`), named by `[apps.<app>] api_key_file` |
| `linger` | `loginctl enable-linger`, so the units outlive your login | the session manager |
| `units` | Writes `weightroom.service` and one unit per installed application, reloads, starts them, waits for each `/api/v1/health` | `~/.config/systemd/user/*.service` |

Nothing in the wizard runs `sudo`. Where a root-owned change would help (the polkit rule for the
Ollama restart button), the wizard prints the command and stops there.

**Re-running is safe.** Every step is idempotent: an existing certificate is kept, an existing
account is kept, the units are regenerated whole (`wr-gym units sync` does the same on its own).

**No unit is enabled at boot.** The operator's standing decision (2026-09-10): the four
applications and `weightroom.service` are started by hand or from the console, not at login.

## 3. Serving

```bash
systemctl --user start weightroom        # the unit the wizard wrote — or, without systemd:
wr-gym serve
```

`wr-gym serve` refuses to start off loopback without the certificate (`TLS_MISSING`), without an
operator account (`INSECURE_BINDING`) or without `server.allowed_hosts` (`INSECURE_BINDING`),
each naming the `setup` step that fixes it. On loopback with no account the console is open — the
operating-system user boundary is the boundary — and says so on the login page.

There is **no plain HTTP** on the console port: `curl http://<host>:8769/` connects to nothing.
The trust listener on `server.trust_port` (8770) serves exactly two routes over plain HTTP —
`/root.crt` and `/trust` — and refuses every other path with `404` and no cookie.

## 4. Trusting the certificate on each device

Open `http://<host>:8770/trust` on the device. The page shows the root's SHA-256 fingerprint —
compare it with `wr-gym trust` on the host before installing anything — and the steps for the
device's operating system. The steps in full, per OS, are
[`LAN_ACCESS.md` §3](LAN_ACCESS.md#3-trusting-the-certificate-on-each-client); in short:

| Device | Where the root goes |
|---|---|
| Linux (Debian/Ubuntu) | `/usr/local/share/ca-certificates/wr-gym.crt`, then `sudo update-ca-certificates`; Firefox imports it under *Authorities* itself |
| macOS | Keychain Access → System → *Always Trust* for SSL |
| Windows | `certmgr.msc` → Trusted Root Certification Authorities |
| iOS / iPadOS | Settings → Profile Downloaded → Install, **then** Settings → General → About → Certificate Trust Settings → enable |
| Android | Settings → Security → Encryption & credentials → Install a certificate → **CA certificate** (not VPN & app) |

Then open `https://<host>.local:8769` (or the LAN address): the padlock, the login page. The
same root serves the leaf for its whole life; `wr-gym tls renew` (automatic inside 30 days of
expiry) changes nothing a device has to trust again. Only `wr-gym tls rotate` replaces the root —
every device trusts it again, and every session is revoked.

## 5. What the console reaches

* The four applications, over HTTP on loopback (`[apps.<name>] base_url`), through their CLIs
  (`[apps.<name>] executable`) and, read-only, through their databases (the URL each one reports
  from its own `config show`). A raw write into one of them passes the five-part guard of
  [ADR-0124](adr/0124-a-raw-write-into-another-applications-database-passes-a-five-part-guard.md)
  or does not happen.
* `systemctl --user` and `journalctl --user` for the units and their logs; `systemctl show` and
  the system journal for `ollama.service`.
* Ollama's own HTTP API (`[host] ollama_base_url`) for residency and pulls.
* Nothing else. Chat goes through LoadCoach and PromptCadence; no provider is ever contacted
  from this process (`tests/security/test_chat_isolation.py`).

## 6. Where things are

| | Path |
|---|---|
| Configuration | `~/.config/wr-gym/config.toml` (`wr-gym config path`); the full reference is [`configuration.md`](configuration.md) |
| Certificates | `~/.config/wr-gym/tls/` |
| Application tokens | `~/.config/wr-gym/secrets/` |
| Database | `~/.local/share/wr-gym/weightroom.sqlite3` |
| Own backups | `~/.local/share/wr-gym/backups/` |
| Guarded-write undo copies | `~/.local/share/wr-gym/backups/<app>/`, kept `[storage] guarded_backup_days` |
| Chat attachments | `~/.local/share/wr-gym/attachments/` |
| Units | `~/.config/systemd/user/{weightroom,freeweight,loadcoach,ideapress,promptcadence}.service` |
| The docs the viewer serves | `[docs] root` — the `docs/` beside the checkout by default; the viewer refuses to start without one |

## 7. After setup

* `wr-gym doctor` — every rule this host is held to, worst first, with the command that fixes
  each. [`troubleshooting.md`](troubleshooting.md) walks the findings.
* `wr-gym apps status` — the four applications and Ollama in one table.
* The Docs tab serves this documentation tree, searchable, with the ADR index.
