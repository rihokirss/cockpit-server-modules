# Cockpit PM2

Cockpit extension for managing PM2 applications across normal Linux user accounts.

## Features

- per-user PM2 process isolation through `HOME` and `PM2_HOME`;
- process status, CPU, memory, uptime and restart counters;
- start, stop, restart, reload, reset and explicit delete actions;
- application creation with working directory, interpreter, arguments, environment,
  cluster mode, watch mode and memory restart limit;
- optional publication below a shared HTTPS domain path through Cockpit Reverse Proxy;
- auto-refreshing, auto-scrolling application logs;
- PM2 process-list save/restore and per-user systemd startup management;
- root-only audit log at `/var/log/cockpit-pm2-audit.jsonl`.

The helper only exposes regular interactive Linux users (UID 1000 or newer) and
executes PM2 through `runuser` as the selected account. Environment values are
accepted when a new application is created, but are never returned to the UI.

## Install

```bash
sudo ../install.sh pm2
```

PM2 must already be installed for each account that should be selectable. Global
installations, `~/.local/bin/pm2`, and NVM installations are detected.
