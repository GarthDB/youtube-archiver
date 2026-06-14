# Fork Setup Guide

This guide walks you through setting up your own automated archiver for a ward YouTube
channel by forking this repository.  The whole process takes about 20 minutes the first
time.

## How it works

- A GitHub Actions workflow runs **twice a week** (Tue/Fri 05:00 UTC).
- It reads your channel ID from a **GitHub Actions Variable** (not a secret — channel IDs
  are public information).
- It authenticates to YouTube using a **refresh token stored as a GitHub Secret** — the
  token is never committed to git.
- Videos that are live broadcasts, still public, and older than 24 hours are set to
  **Unlisted**.

---

## Step 1 — Fork and enable Actions

1. Click **Fork** on the repository page.
2. In your fork, go to **Settings → Actions → General** and set
   _"Allow all actions and reusable workflows"_, then click **Save**.
   (GitHub disables workflows on forks by default.)

---

## Step 2 — Google Cloud: API credentials

You need a **Google Cloud project** connected to your ward's YouTube channel account.

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (e.g. "Ward YouTube Archiver").
3. **Enable the YouTube Data API v3**:
   _APIs & Services → Library → search "YouTube Data API v3" → Enable_.
4. **Configure the OAuth consent screen**:
   _APIs & Services → OAuth consent screen_
   - User type: **External**
   - Fill in App name, support email, developer contact email.
   - Add scope: `https://www.googleapis.com/auth/youtube`
   - Add your Google account (the one that manages the ward channel) as a **Test user**.
   - Click **Save and Continue** through all steps.

5. **⚠️ CRITICAL — Publish the consent screen to "In production"**:
   _APIs & Services → OAuth consent screen → Publishing status → **Publish App**_

   > If you skip this step, your refresh token **expires after 7 days** and the
   > scheduled job will silently start failing.  Publishing the app to production
   > gives you a long-lived refresh token.  (The app doesn't need to pass Google's
   > review for this use case — it's just your own account accessing your own channel.)

6. **Create OAuth credentials**:
   _APIs & Services → Credentials → Create credentials → OAuth client ID_
   - Application type: **Desktop app**
   - Name: "YouTube Archiver"
   - Click **Create**, then **Download JSON**.
   - Save the downloaded file as `credentials.json` in the project root.

---

## Step 3 — Authenticate locally

You'll do the OAuth browser flow once on your machine to generate a refresh token.

```bash
# Clone your fork
git clone https://github.com/<your-username>/youtube-archiver.git
cd youtube-archiver

# Install the package
python3 -m venv .venv && source .venv/bin/activate
pip install -e .

# Authenticate — a browser window will open.
# Sign in as the Google account that has Manager access to the ward's YouTube channel.
youtube-archiver auth setup --config config/example.yml
```

After completing the browser flow, a `token.json` file is saved in the project root.
This file contains your refresh token — keep it private.

---

## Step 4 — Upload secrets and set variables

### Option A — Automated (recommended if you have the `gh` CLI)

```bash
# Install gh CLI if needed: https://cli.github.com/
gh auth login

# Run the setup script — it will encode and upload everything
scripts/setup-github-secrets.sh
```

The script will prompt for your channel ID and optionally the other Variables, then set
everything in your fork's Settings.

### Option B — Manual

#### Export base64 values

```bash
youtube-archiver auth export --credentials --config config/example.yml
```

This prints two base64 blobs you'll need to paste.

#### Set Secrets

Go to **your fork → Settings → Secrets and variables → Actions → Secrets**:

| Secret name                 | Value                                      |
|-----------------------------|--------------------------------------------|
| `YOUTUBE_CREDENTIALS_JSON`  | base64-encoded `credentials.json`          |
| `YOUTUBE_TOKEN_JSON`        | base64-encoded `token.json`                |

#### Set Variables

Go to **your fork → Settings → Secrets and variables → Actions → Variables**:

| Variable name       | Required | Example / Default               | Notes                                 |
|---------------------|----------|---------------------------------|---------------------------------------|
| `WARD_CHANNEL_ID`   | ✅ Yes   | `UCxxxxxxxxxxxxxxxxxxxxxxxxx`   | 24-char channel ID from YouTube Studio → Settings → Channel → Advanced → Channel ID |
| `WARD_NAME`         | No       | `1st Ward`                      | Display name in logs                  |
| `STAKE_NAME`        | No       | `Example Stake`                 | Display name in logs                  |
| `TECH_SPECIALIST`   | No       | `tech@example.com`              | Contact shown in logs                 |
| `WARD_TIMEZONE`     | No       | `America/Denver`                | IANA timezone                         |
| `TARGET_VISIBILITY` | No       | `unlisted` (default)            | `unlisted` or `private`               |

---

## Step 5 — Test with a dry run

Go to **Actions → Archive Live Broadcasts → Run workflow**:
- Set **dry_run** = `true`
- Click **Run workflow**

Check the run log.  It should:
1. Decode credentials from secrets (no errors).
2. List any live broadcast videos that are currently public and older than 24 hours.
3. Show `DRY RUN: Found N videos` (or "No videos found" if all are already archived).

If it errors, see Troubleshooting below.

---

## Step 6 — First live run

Run the workflow again with **dry_run = false**.  The workflow will change eligible
videos to Unlisted.  Verify in YouTube Studio that the visibility changed, then leave
the cron schedule to run automatically on Tuesdays and Fridays.

---

## Multiple wards / channels

To manage more than one ward channel from the same fork:

1. Edit `config/ci.yml` directly — add additional entries under `channels:`.
   Each entry can use its own `${VAR}` references (e.g. `${WARD2_CHANNEL_ID}`).
2. Add the corresponding Variables in repo Settings.
3. The workflow processes all `enabled: true` channels in a single run.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| "Invalid client" / auth error after ~7 days | Consent screen still in "Testing" | Publish to production (Step 2.5 above), run `auth setup` again, re-export token |
| "Workflow never runs" | Actions not enabled on fork | Settings → Actions → General → Allow all |
| "Channel not found" | Wrong channel ID | Confirm in YouTube Studio → Settings → Channel → Advanced → Channel ID (starts with UC, 24 chars) |
| "Quota exceeded" | Too many API calls | The daily quota is 10,000 units; each run uses ~3-5 units/video. Reduce `max_videos_per_channel` in `config/ci.yml` if needed |
| "No videos found" | All videos already unlisted, or `is_live_content` not detected | Check YouTube Studio — if videos show as Unlisted, archiver already ran. If they show as Public, check that the channel actually uses live streams |
| "POLICY BREACH" warning | A video has been public >168h | A prior scheduled run was missed. The video will be archived in this run; check that the cron is enabled and the workflow isn't consistently failing |

---

## Maintaining your fork

- The **token.json** never expires as long as the consent screen is "In production" and
  you don't revoke access in your Google account.
- If you ever need to re-authenticate (e.g. after revoking), repeat Steps 3-4.
- Pull upstream changes periodically to pick up bug fixes:
  ```bash
  git fetch upstream && git merge upstream/main
  ```
