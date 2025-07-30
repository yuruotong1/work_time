# Work Time Tracker

A desktop application for tracking work time using Notion as a database backend.

## Features

- Connect to Notion database to fetch task list
- Start/stop time tracking for selected tasks
- Automatic screenshot capture every 5 minutes
- Real-time data sync back to Notion
- Modern PyQt6-based user interface

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure your Notion credentials in `config.yaml`:
```yaml
notion:
  api: "your_notion_integration_token"
  database_id: "your_database_id"
```

3. Run the application:
```bash
python main.py
```

## Configuration

- Set your Notion integration token in `config.yaml`
- Configure your Notion database ID
- Customize screenshot interval (default: 5 minutes)
- Adjust database column mappings if needed 