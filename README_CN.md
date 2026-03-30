# Work Time Tracker — 远程团队工作时间管理工具

> 专为远程团队设计的桌面工作助手，以 Notion 作为统一的任务分配与时间管理中台，帮助团队成员高效记录工时、留存工作截图，让远程协作更透明、可量化。

**Language / 语言 / 言語:** [English](./README.md) | [中文](./README_CN.md) | [日本語](./README_JA.md)

---

## 它能解决什么问题？

远程工作最大的挑战之一是**工时不透明**：任务分配靠口头确认，工作时长难以追踪，计费核算全凭记忆，团队协作效率低下。

Work Time Tracker 通过与 Notion 打通，将每个人的任务执行情况——包括工作时长和工作截图——自动同步回 Notion 数据库，让项目负责人可以实时了解各成员的工作投入，辅助进行任务分配、工时统计和价值核算。

---

## 核心功能

### 任务管理
- 自动从 Notion 数据库拉取当前任务列表（支持"未开始"和"进行中"状态）
- 任务信息展示：负责人、截止日期、已累计工时
- 一键刷新任务列表

### 时间追踪
- 精准计时：选中任务后一键开始/停止
- 时间自动累加：每次工作会话的时长叠加到 Notion 数据库中
- 时间是核心数据，**优先同步，保障计费准确**

### 自动截图
- 工作期间每隔 5 分钟自动截图，记录真实工作状态
- 多张截图自动拼合为一张网格图（2列）上传至 Notion，避免图片数量爆炸
- Notion 中最多保留最近 20 张拼图（约 20 个工作 session），自动淘汰最旧的

### 可靠的离线同步机制
- **本地优先**：停止计时后立刻将数据写入本地 `pending_uploads.json`，断网、崩溃都不丢失
- **时间与截图解耦**：时间先上传（影响计费）；截图失败不影响时间同步
- **无限重试**：后台线程每 2 分钟自动重试，网络恢复后无需手动操作
- **跨启动续传**：重新打开应用时自动检测并继续上传历史未完成记录
- **实时状态提示**：界面明确显示"时间已同步 ✓"或"截图后台重试中"

---

## 适用场景

| 场景 | 说明 |
|------|------|
| 远程开发团队 | 按任务记录工时，辅助项目报价和结算 |
| 设计/创意团队 | 截图留存工作过程，方便复盘和汇报 |
| 外包接单者 | 自动生成工时记录，增加客户信任度 |
| 小型创业公司 | 以 Notion 为中台统一分配任务、查看各成员投入 |

---

## 快速开始

### 方法一：直接下载 exe（推荐，Windows 用户）

1. 从 [Releases 页面](https://github.com/yuruotong1/work_time/releases) 下载最新的 `WorkTimeTracker.exe`
2. 创建配置文件（见下方[配置说明](#配置说明)）
3. 双击运行，无需安装 Python

### 方法二：从源码运行

**1. 安装依赖**
```bash
pip install -r requirements.txt
```

**2. 创建配置文件**（见下方[配置说明](#配置说明)）

**3. 启动应用**
```bash
python main.py
```

---

## 配置说明

程序按以下优先级查找 `config.yaml`：

| 优先级 | 路径 | 适用场景 |
|--------|------|----------|
| 第一 | `~/.work_time/config.yaml` | 所有用户（exe 和源码均适用） |
| 第二 | `./config.yaml` | 开发调试时备用 |

### 第一步 — 创建配置目录和文件

**Windows：**
```
mkdir %USERPROFILE%\.work_time
copy config.yaml.example %USERPROFILE%\.work_time\config.yaml
```
然后用记事本编辑 `C:\Users\你的用户名\.work_time\config.yaml`。

**macOS / Linux：**
```bash
mkdir -p ~/.work_time
cp config.yaml.example ~/.work_time/config.yaml
```

### 第二步 — 填写 Notion 凭证

```yaml
notion:
  api: "secret_xxxxxxxxxxxxxxxxxxxx"          # Notion Integration Token
  database_id: "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # 数据库 ID（32位）

# 必须与你的 Notion 数据库字段名完全一致
database:
  task_name: 任务名称
  assignee: 负责人
  status: 状态
  time_spent: 工作时间（分钟）
  screenshots: 截屏
  due_date: 截止日期
```

### 第三步 — 获取 Notion 凭证

**Integration Token：**
1. 访问 https://www.notion.so/my-integrations
2. 点击 **"新建集成"**，填写名称后提交
3. 复制 **内部集成 Token**（以 `secret_` 开头）

**数据库 ID：**
1. 在浏览器中打开你的 Notion 数据库页面
2. URL 格式为：`https://www.notion.so/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx?v=...`
3. 复制 `.so/` 和 `?v=` 之间的 32 位字符串，即为数据库 ID

**将集成连接到数据库：**
1. 打开 Notion 数据库页面 → 右上角 `...` 菜单 → **连接** → 选择你创建的集成

---

## Notion 数据库配置

需要在 Notion 中创建一个包含以下字段的数据库：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| 任务名称 | Title | 任务标题 |
| 负责人 | Select | 任务负责人 |
| 状态 | Status | 未开始 / 进行中 / 已完成 |
| 工作时间（分钟） | Number | 累计工时（分钟），自动更新 |
| 截屏 | Files | 工作截图拼图，自动上传 |
| 截止日期 | Date | 任务截止日期 |

> 字段名可在 `config.yaml` 的 `database` 节中自定义映射。

---

## 工作流示意

```
Notion 数据库（任务分配）
        ↓  拉取任务列表
Work Time Tracker（桌面端）
        ↓  开始计时 + 自动截图
        ↓  停止后立即存本地
        ↓  后台自动同步（无限重试）
Notion 数据库（工时 + 截图更新）
        ↓
项目负责人查看各成员工时投入
```

---

## 本地数据文件

| 文件 | 说明 |
|------|------|
| `~/.work_time/config.yaml` | 你的 Notion 凭证和字段映射配置 |
| `pending_uploads.json` | 待同步队列，记录所有未上传的工作会话 |
| `screenshots/` | 本地截图目录，原始截图保存在此 |
| `work_tracker.log` | 运行日志，包含所有同步状态和错误记录 |

---

## 打包为 Windows exe

```powershell
# Windows PowerShell
.\pack_windows.ps1
```

或使用 GitHub Actions 自动构建（推送 tag 触发）：
```bash
git tag v1.x.x
git push origin v1.x.x
```

---

## 技术栈

- **UI**: PyQt6
- **后端**: Notion API (notion-client)
- **截图**: Pillow (PIL)
- **打包**: PyInstaller
- **CI/CD**: GitHub Actions
