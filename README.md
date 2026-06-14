# Odoo 19 + PostgreSQL 18 — Docker Setup

A complete, ready-to-run local development setup for Odoo 19 (latest) with PostgreSQL 18 (latest stable).

---

## Versions

| Service | Version | Notes |
|---------|---------|-------|
| Odoo | 19 | Latest stable — released Oct 2025 |
| PostgreSQL | 18 | Latest stable — released May 2026 |

---

## Project Structure

```
odoo-docker/
├── docker-compose.yml      # Main compose file
├── .env                    # Environment variables
├── .gitignore
├── config/
│   └── odoo.conf           # Odoo configuration
├── addons/                 # Your custom Odoo modules go here
├── logs/                   # Odoo log files (auto-created)
└── postgresql/             # Postgres data directory (auto-created)
```

---

## Quick Start

### 1. Prerequisites
Make sure Docker Desktop is installed and running:
- **Windows/Mac**: https://www.docker.com/products/docker-desktop
- **Linux**: `sudo apt install docker.io docker-compose-plugin`

### 2. Start the stack

```bash
docker compose up -d
```

This will:
- Pull `odoo:19` and `postgres:18` images (first run takes a few minutes)
- Start PostgreSQL and wait until it's healthy
- Start Odoo connected to the database

### 3. Open Odoo

Visit: **http://localhost:8069**

On first visit you'll see the **database creation screen**:
- **Master Password**: `MyStr0ngMasterPass!` ← change this in `config/odoo.conf`
- **Database Name**: choose any name (e.g. `mycompany`)
- **Email / Password**: your Odoo admin credentials
- Click **Create database**

---

## Common Commands

| Task | Command |
|------|---------|
| Start (background) | `docker compose up -d` |
| Stop | `docker compose down` |
| View logs (live) | `docker compose logs -f odoo` |
| Restart Odoo only | `docker compose restart odoo` |
| Open Odoo shell | `docker exec -it odoo_app odoo shell -d YOUR_DB_NAME` |
| Open psql | `docker exec -it odoo_postgres psql -U odoo -d postgres` |
| Full reset (delete all data) | `docker compose down -v && rm -rf postgresql/ logs/` |

---

## Configuration

### Change the master password (recommended!)
Edit `config/odoo.conf`:
```ini
admin_passwd = YourNewStrongPassword
```
Then restart: `docker compose restart odoo`

### Add custom modules
Drop your module folder into `addons/` then:
```bash
docker compose restart odoo
# In Odoo UI: Settings → Activate Developer Mode → Update Apps List
```

### Production workers
In `config/odoo.conf`, set workers based on your CPU count:
```ini
workers = 4   # (2 × CPU cores) + 1
```

---

## Ports

| Service | Port | Description |
|---------|------|-------------|
| Odoo Web | 8069 | Main web interface |
| Odoo Longpoll | 8072 | Live chat / real-time |
| PostgreSQL | 5432 | Direct DB access |

---

## Connecting a DB client (e.g. pgAdmin, DBeaver)

| Field | Value |
|-------|-------|
| Host | `localhost` |
| Port | `5432` |
| Username | `odoo` |
| Password | `odoo_password` |
| Database | `postgres` (or your Odoo DB name) |
