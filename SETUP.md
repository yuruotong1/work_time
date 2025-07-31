# Setup Instructions

## 1. Notion Integration Setup

### Create Notion Integration
1. Go to [https://www.notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Click "New integration"
3. Give it a name (e.g., "Work Time Tracker")
4. Select the workspace where your database is located
5. Set capabilities:
   - Read content
   - Update content
6. Click "Submit"
7. Copy the "Internal Integration Token"

### Get Database ID
1. Open your Notion database in the browser
2. Copy the database ID from the URL:
   ```
   https://www.notion.so/workspace/DATABASE_ID?v=...
   ```
3. The database ID is the long string after the workspace name

### Share Database with Integration
1. Open your database in Notion
2. Click "Share" in the top right
3. Click "Invite"
4. Search for your integration name
5. Select it and click "Invite"

## 2. Database Structure

Your Notion database should have these properties:

### Required Properties
- **任务名称** (Title): Task name
- **人员** (People): Task assignee

### Optional Properties
- **工作时间（分钟）** (Number): Total time spent on task (in minutes)
- **截屏** (Files): Screenshot files
- **截止日期** (Date): Task due date

### Example Database Structure
```
| 任务名称 | 人员 | 工作时间（分钟） | 截屏 | 截止日期 |
|----------|------|----------------|------|----------|------|
| 开发项目 | 高晓阳 | 60.0 | screenshot_20231201_143022.png | 2024-01-15  |
| 设计任务 | 张三 | 0 | | 2024-01-20 |
```

## 3. Configuration Setup

1. Edit `config.yaml` with your actual values:
   ```yaml
   notion:
     api: "secret_your_actual_token_here"
     database_id: "your_actual_database_id_here"
   
       # Database column mappings (adjust if your column names are different)
    database:
      task_name: "任务名称"
      assignee: "人员"
      time_spent: "工作时间（分钟）"
      screenshots: "截屏"
      due_date: "截止日期"
   ```

## 4. Install Dependencies

```bash
pip install -r requirements.txt
```

## 5. Run the Application

```bash
python main.py
```

## Troubleshooting

### Connection Issues
- Verify your Notion token is correct
- Ensure the database ID is correct
- Check that the integration has access to the database

### Database Structure Issues
- Make sure your database has a "Name" (Title) property
- Ensure "Status" property exists and is a Select type
- Check that the integration has permission to read/write the database

### Screenshot Issues
- The application creates a "screenshots" folder in the current directory
- Ensure the application has permission to write to the current directory
- Screenshots are saved as PNG files with timestamps 