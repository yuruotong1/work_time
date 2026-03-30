# Work Time Tracker

> A desktop companion for remote teams — track task time, capture screenshots automatically, and sync everything to Notion.

**Language / 语言 / 言語:** [English](./README.md) | [中文](./README_CN.md) | [日本語](./README_JA.md)

---

## What Problem Does It Solve?

One of the biggest challenges in remote work is **lack of transparency around time investment**: tasks are assigned verbally, hours worked are hard to verify, and billing relies on memory. Work Time Tracker bridges this gap by automatically syncing each team member's task time and work screenshots back to a shared Notion database — giving managers real-time visibility into how time is being spent.

---

## Core Features

### Task Management
- Pulls your task list directly from a Notion database (filters "Not Started" and "In Progress" statuses)
- Displays assignee, due date, and cumulative hours per task
- One-click refresh

### Time Tracking
- Start / stop a timer per task with a single click
- Time accumulates across multiple sessions — each session adds to the Notion total
- **Time is synced first** — it's the data that drives billing and valuation

### Automatic Screenshots
- Takes a screenshot every 5 minutes while tracking
- Merges all screenshots from a session into a single 2-column collage and uploads it to Notion — no image count explosion
- Notion keeps the 20 most recent collages per task; older ones are trimmed automatically

### Reliable Offline Sync
- **Local-first**: on stop, session data is immediately written to `pending_uploads.json` — survives network failures and crashes
- **Time and screenshots are decoupled**: if screenshot upload fails, time is still synced
- **Infinite retry**: a background thread retries every 2 minutes until everything is uploaded
- **Resumes on restart**: pending sessions from previous runs are automatically retried on next launch
- **Live status**: the UI clearly shows `Time synced ✓` or `Screenshots retrying in background`

---

## Use Cases

| Scenario | Benefit |
|----------|---------|
| Remote development teams | Track hours per task for accurate project billing |
| Design / creative teams | Screenshot log provides a visual record of work for review |
| Freelancers | Auto-generated time logs build client trust |
| Small startups | Use Notion as a central hub for task assignment and time visibility |

---

## Quick Start

### Option A — Download the exe (Windows, recommended)

1. Download the latest `WorkTimeTracker.exe` from the [Releases page](https://github.com/yuruotong1/work_time/releases)
2. Create the config file (see [Configuration](#configuration) below)
3. Double-click `WorkTimeTracker.exe` to run — no Python installation required

### Option B — Run from source

**1. Install dependencies**
```bash
pip install -r requirements.txt
```

**2. Create the config file** (see [Configuration](#configuration) below)

**3. Run**
```bash
python main.py
```

---

## Configuration

The app reads `config.yaml` from the following locations (in order):

| Priority | Path | Recommended for |
|----------|------|-----------------|
| 1st | `~/.work_time/config.yaml` | All users (exe & source) |
| 2nd | `./config.yaml` | Development / running from source |

### Step 1 — Create the config directory and file

**Windows:**
```
mkdir %USERPROFILE%\.work_time
copy config.yaml.example %USERPROFILE%\.work_time\config.yaml
```
Then edit `C:\Users\<YourName>\.work_time\config.yaml`.

**macOS / Linux:**
```bash
mkdir -p ~/.work_time
cp config.yaml.example ~/.work_time/config.yaml
```

### Step 2 — Fill in your Notion credentials

```yaml
notion:
  api: "secret_xxxxxxxxxxxxxxxxxxxx"       # Your Notion Integration Token
  database_id: "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # 32-char ID from your database URL

# Must match your Notion database field names exactly
database:
  task_name: Task Name
  assignee: Assignee
  status: Status
  time_spent: Time Spent (minutes)
  screenshots: Screenshots
  due_date: Due Date
```

### Step 3 — Get your Notion credentials

**Integration Token:**
1. Go to https://www.notion.so/my-integrations
2. Click **"New integration"**, give it a name, and click **Submit**
3. Copy the **Internal Integration Token** (starts with `secret_`)

**Database ID:**
1. Open your Notion database page in a browser
2. The URL looks like: `https://www.notion.so/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx?v=...`
3. Copy the 32-character string between `.so/` and `?v=` — that's your database ID

**Connect the Integration to your database:**
1. In your Notion database → top-right `...` menu → **Connections** → select your Integration

---

## Notion Database Setup

Create a database with the following fields:

| Field | Type | Description |
|-------|------|-------------|
| Task Name | Title | Task title |
| Assignee | Select | Team member responsible |
| Status | Status | Not Started / In Progress / Done |
| Time Spent (minutes) | Number | Cumulative minutes — auto-updated |
| Screenshots | Files | Session collage — auto-uploaded |
| Due Date | Date | Task deadline |

> Field names are configurable via the `database` section in `config.yaml`.

---

## How It Works

```
Notion Database (task assignment)
        ↓  fetch task list
Work Time Tracker (desktop)
        ↓  start timer + auto screenshot
        ↓  stop → save locally immediately
        ↓  background sync (infinite retry)
Notion Database (time + screenshot updated)
        ↓
Manager reviews each member's time investment
```

---

## Local Data Files

| File | Description |
|------|-------------|
| `~/.work_time/config.yaml` | Your credentials and column mappings |
| `pending_uploads.json` | Upload queue — sessions waiting to sync |
| `screenshots/` | Raw screenshot files |
| `work_tracker.log` | Full sync log with errors and retry status |

---

## Build Windows EXE

```powershell
.\pack_windows.ps1
```

Or trigger a GitHub Actions build by pushing a tag:
```bash
git tag v1.x.x
git push origin v1.x.x
```

---

## Tech Stack

- **UI**: PyQt6
- **Backend**: Notion API (notion-client)
- **Screenshots**: Pillow (PIL)
- **Packaging**: PyInstaller
- **CI/CD**: GitHub Actions
