# Restarting Ollama from WeightRoomGym — the polkit rule, for any operator

**Audience:** an operator who wants the console's *Restart Ollama* button to work, on any host,
for one account or several. **Decision this implements:**
[ADR-0125](adr/0125-weightroom-drives-the-applications-through-systemd-user-units-it-writes.md)
rule 5 — Ollama is a **system** unit its own installer wrote, WeightRoomGym runs as an ordinary
user and never runs `sudo`, so a restart needs a grant installed by root, and the grant is a polkit
rule.

**Status (2026-09-09):** the rule is optional. Without it the console reads Ollama fully (state,
the `MEMORY_SAFETY.md` §2.1 checklist, resident models) and shows the restart as a command to run.

---

## 1. What the rule grants, and what it does not

| Grants | Does not grant |
|---|---|
| `start`, `stop`, `restart` of **one unit** (`ollama.service`, or whatever `[host] ollama_unit` names) | Any other unit, `systemctl` in general, `sudo`, or any other polkit action |
| To **one OS account**, or to the members of **one group** | To anyone who is merely logged into the console from a browser |
| Without a password prompt | Anything at all on a host where the file is not installed |

**Why polkit and not a `sudoers` line.** A `sudoers` `NOPASSWD` entry grants a *command*; polkit
grants an *action on a unit with a verb*. The narrower grant is the right one for a console that
answers from the LAN (ADR-0125 rule 5, ADR-0126).

**Why the rule does not check `subject.local` or `subject.active`.** `wr-gym` runs as a
`systemd --user` service, not inside an active desktop session. systemd's own default for this
action is `auth_admin` for any subject that is not in one — check with
`pkaction --verbose --action-id org.freedesktop.systemd1.manage-units`. A rule that also required
an active local session would never match the service, and the button would keep being refused.

---

## 2. Which account is "the user"

The rule names the **operating-system account that runs `wr-gym`**, not the username you log into
the console with. They are often the same word; they are different things.

```bash
# The account that owns the running console (the `weightroom` user unit):
ps -o user= -C wr-gym | sort -u
# or, before it is running, the owner of its configuration:
stat -c %U ~/.config/wr-gym/config.toml
```

Also check the unit name WeightRoomGym will restart (default `ollama.service`):

```bash
wr-gym config show | grep ollama_unit
systemctl show -p Id --value ollama.service     # confirm the unit exists under that name
```

The console's *Ollama* page and `wr-gym doctor` print the rule already filled in with both values
for the machine they run on; this document is the same rule, written for any host.

---

## 3. Variant A — one operator account

Set the two values, then install. The heredoc is **unquoted on purpose** so the shell substitutes
`$OPERATOR` and `$UNIT`; the rule body contains no other `$`.

```bash
OPERATOR=jordan              # the account from §2
UNIT=ollama.service          # [host] ollama_unit

sudo tee /etc/polkit-1/rules.d/50-weightroom-ollama.rules >/dev/null <<EOF
// /etc/polkit-1/rules.d/50-weightroom-ollama.rules
// Lets one user start, stop and restart one unit, without a password and without granting
// systemctl. WeightRoomGym (ADR-0125 rule 5); see docs/OLLAMA_RESTART_POLKIT.md.
polkit.addRule(function (action, subject) {
    if (action.id == "org.freedesktop.systemd1.manage-units" &&
        action.lookup("unit") == "$UNIT" &&
        (action.lookup("verb") == "restart" || action.lookup("verb") == "start" ||
         action.lookup("verb") == "stop") &&
        subject.user == "$OPERATOR") {
        return polkit.Result.YES;
    }
});
EOF
sudo chmod 0644 /etc/polkit-1/rules.d/50-weightroom-ollama.rules
```

Read the file back before trusting it — the two substituted lines must show real values, not
empty quotes:

```bash
sudo grep -nE 'lookup\("unit"\)|subject\.user' /etc/polkit-1/rules.d/50-weightroom-ollama.rules
```

---

## 4. Variant B — several operator accounts, through a group

For a host where more than one account runs a console (or may, later), grant a **group** instead
and manage membership with ordinary account tools. Use one variant or the other, not both.

```bash
GROUP=wr-gym-ollama
UNIT=ollama.service

sudo groupadd --system "$GROUP"
sudo usermod -aG "$GROUP" jordan          # repeat per operator account
sudo usermod -aG "$GROUP" alex

sudo tee /etc/polkit-1/rules.d/50-weightroom-ollama.rules >/dev/null <<EOF
// /etc/polkit-1/rules.d/50-weightroom-ollama.rules
// Lets members of one group start, stop and restart one unit, without a password and without
// granting systemctl. WeightRoomGym (ADR-0125 rule 5); see docs/OLLAMA_RESTART_POLKIT.md.
polkit.addRule(function (action, subject) {
    if (action.id == "org.freedesktop.systemd1.manage-units" &&
        action.lookup("unit") == "$UNIT" &&
        (action.lookup("verb") == "restart" || action.lookup("verb") == "start" ||
         action.lookup("verb") == "stop") &&
        subject.isInGroup("$GROUP")) {
        return polkit.Result.YES;
    }
});
EOF
sudo chmod 0644 /etc/polkit-1/rules.d/50-weightroom-ollama.rules
```

Removing someone's access is `sudo gpasswd -d <account> wr-gym-ollama`; the rule file does not
change. The group form widens the grant to every member's console, so keep the group to operator
accounts only.

---

## 5. Narrowing it further

The console itself only ever **restarts**. `start` and `stop` are granted so the same operator can
recover a stopped daemon from a terminal without `sudo`. For a restart-only grant, replace the verb
test with:

```javascript
        action.lookup("verb") == "restart" &&
```

---

## 6. Check it worked

polkit picks up changes in `/etc/polkit-1/rules.d/` by itself. As the operator account, **not**
with `sudo`:

```bash
# Allowed — note this really restarts Ollama and unloads every resident model:
systemctl --no-ask-password restart "$UNIT" && echo permitted

# Still refused — the grant is one unit, not systemctl (a harmless unit to be refused on):
systemctl --no-ask-password restart systemd-timesyncd.service || echo "refused, as it should be"
```

Then, in the console, press **Restart Ollama** on the *Ollama* page. `wr-gym doctor`'s
`polkit.ollama_restart` finding reads `unknown` until that first attempt and `ok` after it —
polkit will not answer the question in advance for a caller that is not root, so the first real
attempt is the probe (row W2).

---

## 7. Remove it

```bash
sudo rm /etc/polkit-1/rules.d/50-weightroom-ollama.rules
sudo groupdel wr-gym-ollama        # Variant B only
```

The console goes back to printing the restart as a command, and the doctor reports it as not
permitted after the next attempt.

---

## 8. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Interactive authentication required` | The rule is not loaded, or does not match | `journalctl -u polkit -b \| grep -i weightroom` — a syntax error is reported there by file name; re-read the substituted lines (§3) |
| Refused for one account, allowed for another | The rule names a different account than the one running `wr-gym` | §2 — it is the OS account of the `weightroom` unit, not the console login |
| Refused only from the console, allowed from a terminal | The rule checks `subject.active` or `subject.local` | Remove those tests (§1) |
| Refused for a host whose Ollama unit has another name | `action.lookup("unit")` names `ollama.service` | Set `UNIT` to the real name; set `[host] ollama_unit` to match |
| `/etc/polkit-1/rules.d` does not exist, only `localauthority` | polkit older than 0.106, which reads `.pkla` files instead of JavaScript | `pkaction --version`; upgrade polkit — this document does not cover `.pkla` |
| `sudo grep …` shows `== ""` | The heredoc was quoted (`<<'EOF'`) or the variables were unset | Re-run §3 or §4 exactly as written |

---

## 9. Security notes

* **Whoever can log into the console can restart and stop Ollama** once this is installed. That is
  the operator's own daemon and the operator's own console, behind its password, its TLS and its
  rate limit (ADR-0126) — but it is a real reach from the LAN, and the reason the rule is optional.
* **Never drop the unit test.** A rule that returns `YES` for `manage-units` without
  `action.lookup("unit")` grants every system unit on the machine.
* **Never widen `subject.user` to a list you do not control**, and never grant the group to a
  service account that is not an operator.
* The console never writes this file and never runs `sudo`; a test in `tests/security` asserts the
  second (ADR-0125 rule 5).
