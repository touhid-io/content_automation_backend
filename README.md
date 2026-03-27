# Content Automation Engine Backend

A strictly typed, async-first FastAPI backend for running background automation workflows in a multi-tenant SaaS application.

This backend is intentionally focused on **background processing only**. It does **not** handle end-user authentication or direct frontend CRUD operations. Instead, it is responsible for:

- scheduled automation jobs
- external API integrations
- AI-powered content generation
- content cleanup and transformation
- publishing to external channels
- administrative notifications

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Core Responsibilities](#core-responsibilities)
3. [Tech Stack](#tech-stack)
4. [Project Structure](#project-structure)
5. [Environment Variables](#environment-variables)
6. [Database Schema](#database-schema)
7. [How the Automation Flow Works](#how-the-automation-flow-works)
8. [Local Development Setup](#local-development-setup)
9. [Running the Application](#running-the-application)
10. [Deployment Instructions](#deployment-instructions)
11. [Docker Deployment](#docker-deployment)
12. [Platform Deployment Notes](#platform-deployment-notes)
13. [Scheduler and Cron Job Behavior](#scheduler-and-cron-job-behavior)
14. [Security Notes](#security-notes)
15. [Testing](#testing)
16. [Troubleshooting](#troubleshooting)
17. [Future Improvements](#future-improvements)

---

## Architecture Overview

The system is designed as a **background automation engine** that works alongside a frontend-driven SaaS application.

### Responsibility split

**Frontend / Supabase Client SDK**
- user authentication
- direct user-facing CRUD operations
- dashboard/UI interactions
- scheduling content from the frontend

**This backend**
- periodic polling of connected YouTube channels
- transcript extraction from videos
- article generation via Gemini
- article cleanup and normalization
- publishing scheduled content to Facebook and Telegram
- admin notifications for successful publishing

This separation keeps the backend small, focused, and easier to operate.

---

## Core Responsibilities

### 1. Content Fetcher Job
Runs every hour.

For each connected channel:
- checks quota availability
- fetches recent YouTube videos from RSS
- avoids duplicate processing using `source_video_id`
- extracts transcript from the custom transcript API
- generates an article with Gemini 1.5 Pro
- cleans the generated text using regex rules
- stores the output in `posts` as `Draft`

### 2. Publisher Job
Runs every 5 minutes.

- loads due scheduled posts
- reads encrypted user publishing credentials
- decrypts tokens
- publishes to Facebook Page
- optionally publishes to Telegram if user Telegram settings exist
- marks posts as `Published`
- sends admin success notification to the configured Telegram group/chat

---

## Tech Stack

### Framework and runtime
- Python 3.10+
- FastAPI
- Uvicorn

### Validation and configuration
- Pydantic v2
- pydantic-settings
- python-dotenv

### Scheduling
- APScheduler with `AsyncIOScheduler`

### Database access
- Supabase Python client

### AI integration
- Google Gen AI SDK (`google-genai`)
- Gemini 1.5 Pro

### HTTP and integrations
- `httpx` for async HTTP calls
- `requests` for compatibility with the provided transcript extraction logic

### Security
- `cryptography` for reversible token encryption/decryption

---

## Project Structure

```text
content-automation-engine/
├── app/
│   ├── api/
│   │   └── health.py
│   ├── core/
│   │   ├── config.py
│   │   ├── logging.py
│   │   ├── scheduler.py
│   │   └── security.py
│   ├── db/
│   │   └── supabase.py
│   ├── schemas/
│   │   ├── ai.py
│   │   ├── cleaner.py
│   │   ├── common.py
│   │   ├── connected_channel.py
│   │   ├── health.py
│   │   ├── post.py
│   │   ├── publish.py
│   │   ├── user_credentials.py
│   │   └── youtube.py
│   ├── services/
│   │   ├── ai_service.py
│   │   ├── publish_service.py
│   │   ├── text_cleaner_service.py
│   │   └── youtube_service.py
│   ├── tasks/
│   │   ├── content_fetcher.py
│   │   └── publisher.py
│   ├── utils/
│   │   ├── datetime.py
│   │   ├── db.py
│   │   └── exceptions.py
│   └── main.py
├── sql/
│   └── schema.sql
├── tests/
│   ├── conftest.py
│   └── test_text_cleaner_service.py
├── .env.example
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## Environment Variables

Create a `.env` file in the project root.

### Required variables

```env
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=

GEMINI_API_KEY=
YT_EXTRACTOR_API_KEY=

TELEGRAM_BOT_TOKEN=
TELEGRAM_TEST_CHAT_ID=

FACEBOOK_APP_ID=
FACEBOOK_APP_SECRET=
ENCRYPTION_SECRET_KEY=

APP_NAME=Content Automation Engine
APP_VERSION=1.0.0
APP_ENV=development
ENABLE_SCHEDULER=true
LOG_LEVEL=INFO
```

### Variable notes

#### Supabase
- `SUPABASE_URL`: your Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY`: service role key used by the backend for secure background writes and reads

#### Gemini
- `GEMINI_API_KEY`: API key used to call Gemini 1.5 Pro

#### Transcript extraction
- `YT_EXTRACTOR_API_KEY`: API key used by the custom transcript extractor service

#### Telegram
- `TELEGRAM_BOT_TOKEN`: admin bot token used to send backend success notifications
- `TELEGRAM_TEST_CHAT_ID`: admin group/chat ID that receives success notifications

#### Facebook
- `FACEBOOK_APP_ID` and `FACEBOOK_APP_SECRET`: app-level credentials; currently page publishing is driven by user page tokens stored in the database

#### Encryption
- `ENCRYPTION_SECRET_KEY`: used to derive a Fernet-compatible encryption key for token encryption/decryption

### Important
Do not commit `.env` to version control.

---

## Database Schema

The SQL required to create the tables is available in:

```text
sql/schema.sql
```

### Main tables

#### `user_credentials`
Stores per-user integration settings and encrypted publishing credentials.

Fields:
- `id`
- `user_id`
- `fb_page_token`
- `telegram_bot_token`
- `telegram_chat_id`
- `gemini_system_prompt`
- `target_word_count`
- `created_at`
- `updated_at`

#### `connected_channels`
Stores YouTube channels attached to a user account.

Fields:
- `id`
- `user_id`
- `youtube_channel_id`
- `daily_quota`
- `today_processed_count`
- `quota_reset_date`
- `created_at`
- `updated_at`

#### `posts`
Stores processed articles and publishing state.

Fields:
- `id`
- `user_id`
- `channel_id`
- `source_video_id`
- `original_transcript`
- `cleaned_article`
- `thumbnail_url`
- `status`
- `facebook_publish_status`
- `telegram_publish_status`
- `schedule_time`
- `created_at`
- `updated_at`

### Why extra fields were added
A few practical fields were included to make the automation system production-friendly:

- `telegram_chat_id`: needed to know where to publish user Telegram content
- `quota_reset_date`: allows deterministic daily quota resets
- `source_video_id`: prevents duplicate content generation from the same YouTube video

---

## How the Automation Flow Works

### Draft creation flow
1. Scheduler triggers `content_fetcher` every hour.
2. The backend loads all connected channels.
3. It resets quota state when a new UTC date begins.
4. It fetches recent channel videos via YouTube RSS.
5. It skips already-processed videos using `source_video_id`.
6. It calls the custom transcript extraction API.
7. It sends the transcript to Gemini 1.5 Pro.
8. It injects the dynamic instruction:
   - `Strictly write the article in approximately [target_word_count] words.`
9. It cleans the text using regex rules.
10. It stores the generated content in `posts` as `Draft`.

### Publishing flow
1. Scheduler triggers `publisher` every 5 minutes.
2. The backend finds `Scheduled` posts whose `schedule_time` is due.
3. It loads encrypted user tokens.
4. It decrypts tokens using Fernet-based encryption.
5. It publishes the post to Facebook.
6. It immediately marks the post as `Published` and sets `facebook_publish_status` to `Published`.
7. If Telegram credentials are available, it also publishes to Telegram.
8. It updates `telegram_publish_status` to `Published`, `Skipped`, or `Failed` accordingly.
9. It sends a success notification to the admin Telegram chat.

---

## Local Development Setup

### 1. Clone or extract the project
If you downloaded the ZIP, extract it first.

### 2. Create a virtual environment

#### Linux / macOS
```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### Windows PowerShell
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Create your environment file
```bash
cp .env.example .env
```

Then edit `.env` and add your real values.

### 5. Apply database schema in Supabase
Open your Supabase SQL editor and run:

- the contents of `sql/schema.sql`

### 6. Store encrypted tokens in the database
For publishing to work correctly:
- `fb_page_token` should be stored encrypted
- `telegram_bot_token` should be stored encrypted if used for per-user Telegram publishing

Use the `encrypt_token()` helper from `app/core/security.py` when saving tokens from your admin workflow or provisioning pipeline.

---

## Running the Application

### Development mode
```bash
uvicorn app.main:app --reload
```

### Production-like single process
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Health check
Once running:

```text
GET /api/health
```

Example:
```bash
curl http://localhost:8000/api/health
```

Expected response:
```json
{
  "status": "ok"
}
```

---

## Deployment Instructions

You can deploy this backend in several ways. The simplest options are:

- Docker on a VPS
- Render
- Railway
- Fly.io
- any platform that can run a long-lived Python web service

### Core deployment requirement
This app contains an in-process scheduler. That means the deployed service must run as a **persistent web process**.

Avoid deploying this as a purely serverless function unless you move the scheduler to an external cron system.

### Before deploying
Make sure all of these are ready:
- Supabase schema has been applied
- `.env` values are available in the hosting platform
- service role key is configured correctly
- admin Telegram bot is working
- Gemini API key is valid
- transcript extractor API key is valid
- user tokens in DB are encrypted with the same `ENCRYPTION_SECRET_KEY`

---

## Docker Deployment

### Build the image
```bash
docker build -t content-automation-engine .
```

### Run the container
```bash
docker run -d \
  --name content-automation-engine \
  -p 8000:8000 \
  --env-file .env \
  content-automation-engine
```

### Verify
```bash
curl http://localhost:8000/api/health
```

### Recommended Docker production notes
For real production deployments:
- use restart policies
- send logs to a centralized log sink
- store secrets in the platform secret manager, not a local `.env` file
- add a reverse proxy like Nginx or use a managed load balancer

Example with restart policy:
```bash
docker run -d \
  --restart unless-stopped \
  --name content-automation-engine \
  -p 8000:8000 \
  --env-file .env \
  content-automation-engine
```

---

## Platform Deployment Notes

### Option A: Render
1. Create a new Web Service.
2. Connect your repository or upload the code.
3. Set runtime to Python.
4. Build command:
   ```bash
   pip install -r requirements.txt
   ```
5. Start command:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 10000
   ```
6. Add all environment variables from `.env.example` in Render dashboard.
7. Ensure the instance stays awake if you rely on APScheduler.

### Option B: Railway
1. Create a new project.
2. Deploy the repository.
3. Set start command:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
4. Add the environment variables.
5. Verify logs to ensure scheduler startup succeeded.

### Option C: VPS / Ubuntu server
1. Install Python 3.11+.
2. Copy project files to server.
3. Create venv and install requirements.
4. Create `.env`.
5. Run with `uvicorn` directly or behind `systemd`.
6. Put Nginx in front if you want TLS termination.

Example `systemd` service:

```ini
[Unit]
Description=Content Automation Engine
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/opt/content-automation-engine
EnvironmentFile=/opt/content-automation-engine/.env
ExecStart=/opt/content-automation-engine/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Then run:
```bash
sudo systemctl daemon-reload
sudo systemctl enable content-automation-engine
sudo systemctl start content-automation-engine
sudo systemctl status content-automation-engine
```

---

## Scheduler and Cron Job Behavior

The scheduler is started from FastAPI lifespan when:

```env
ENABLE_SCHEDULER=true
```

### Configured jobs
- `content_fetcher_job`: every hour at minute `0`
- `publisher_job`: every 5 minutes

### Important deployment caution
If you run multiple app replicas, each replica will start its own scheduler.

That can cause duplicate automation runs.

### Recommended strategies
Choose one of these patterns:

#### Pattern 1: Single scheduler instance
Run only one app instance with scheduler enabled.

#### Pattern 2: Split web and worker roles
- web service: `ENABLE_SCHEDULER=false`
- worker service: `ENABLE_SCHEDULER=true`

This is the cleanest production strategy.

#### Pattern 3: External cron orchestration
Disable APScheduler and trigger jobs externally using platform cron or a job runner.

---

## Security Notes

### Service role key
`SUPABASE_SERVICE_ROLE_KEY` is highly privileged.
- never expose it to the frontend
- never commit it to Git
- keep it only on the server side

### Token encryption
User tokens should be encrypted before storage.

Relevant helper:
- `app/core/security.py`

### Encryption key stability
Do not change `ENCRYPTION_SECRET_KEY` after tokens are encrypted in production unless you also re-encrypt all stored tokens.

### Logging
Avoid printing raw access tokens or decrypted secrets in logs.

---

## Testing

Run tests with:

```bash
pytest
```

Currently included:
- basic text cleaner unit test
- `conftest.py` for correct test path resolution

You should add more tests for:
- YouTube RSS parsing
- transcript payload normalization
- AI prompt construction
- publisher behavior with skipped Telegram publishing
- quota reset logic
- duplicate video prevention

---

## Troubleshooting

### Scheduler not running
Check:
- `ENABLE_SCHEDULER=true`
- application logs for scheduler startup message
- host platform does not aggressively sleep the instance

### Facebook post not publishing
Check:
- stored page token is valid
- token decrypts successfully
- `thumbnail_url` is publicly reachable
- page token has required permissions

### Telegram publishing skipped
This is expected if either of these is missing:
- `telegram_bot_token`
- `telegram_chat_id`

### Gemini returns empty content
Check:
- `GEMINI_API_KEY`
- transcript content is non-empty
- model access is enabled for the account

### Transcript extraction fails
Check:
- `YT_EXTRACTOR_API_KEY`
- custom extractor service availability
- YouTube URL format

### Duplicate drafts still appear
Check:
- `source_video_id` is being stored correctly
- unique index on `(channel_id, source_video_id)` exists in Supabase

---

## Future Improvements

Recommended next improvements for production maturity:

- add structured JSON logging
- add retry policies for external API failures
- move scheduler jobs into dedicated worker process
- add dead-letter/error tracking table
- add webhook endpoints for manual re-triggering jobs
- add proper test coverage for service and task layers
- add Alembic migrations if SQLAlchemy becomes primary for schema management
- add metrics and observability with Prometheus or OpenTelemetry
- add per-user rate limiting and backoff for publishing retries

---

## Quick Start Summary

```bash
cp .env.example .env
pip install -r requirements.txt
# apply sql/schema.sql in Supabase
uvicorn app.main:app --reload
```

Then verify:
- `/api/health` returns `{"status": "ok"}`
- scheduler logs show startup
- Supabase tables exist
- credentials are configured

---

## Final Note

This codebase is intentionally optimized for a background-automation architecture where the frontend owns user-facing flows and this backend owns scheduled work, integrations, and content publishing. That boundary keeps the system easier to scale, reason about, and secure.
