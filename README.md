# Cockpit Server Modules

Four focused Cockpit extensions for managing a small self-hosted Linux server:

| Module | Cockpit menu | Purpose |
|---|---|---|
| Certificates | Sertifikaadid | Let's Encrypt lifecycle and Synology DSM deployment |
| Reverse Proxy | Reverse Proxy | Nginx virtual hosts, HTTPS, health checks and WebSockets |
| Samba AD DC | Samba Active Directory | Users, groups, computers, DNS, GPOs, backups and diagnostics |
| RADIUS | RADIUS | FreeRADIUS, UniFi clients and Samba AD authentication |

The UI is currently in Estonian. Each package uses Cockpit's privilege escalation
for a small root-owned helper instead of running the browser-facing code as root.

## Requirements

- a recent Cockpit installation;
- Python 3 and the command-line tools used by the selected module;
- Nginx and Certbot for Reverse Proxy and Certificates;
- a configured Samba AD DC for Samba AD and RADIUS;
- FreeRADIUS with `ntlm_auth`/winbind for RADIUS.

These modules manage existing services. They do not provision a Samba domain or
replace the distribution's initial service setup.

## Install

Run the installer as root and select one or more modules:

```bash
sudo ./install.sh certificates reverseproxy samba-ad radius
```

Then open Cockpit and refresh the page. Packages are installed under
`/usr/local/share/cockpit/` and privileged helpers under `/usr/local/libexec/`.

Configuration and credentials are deliberately not stored in this repository.
Runtime secrets are kept in root-only files under `/etc` or passed only for the
duration of an operation.

## Development checks

```bash
python3 -m py_compile cockpit-*/*helper*
node --check cockpit-certificates/app.js
node --check cockpit-reverseproxy/app.js
node --check cockpit-samba-ad/app.js
node --check cockpit-radius/app.js
```

## Security

Cockpit is an administrative interface. Restrict access with a firewall or VPN,
use strong authentication, and review generated service configuration before
deploying these modules on a production system.

## License

MIT
