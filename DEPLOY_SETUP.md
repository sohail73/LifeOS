# LifeOS on Streamlit Cloud -- one-time setup (data-safe)

Goal: open the deployed app with your SAME email + password and see your
SAME data, and never lose it when the app sleeps / reboots / redeploys.

## 1. Private backup repo (GitHub)
1. GitHub > New repository > name `lifeos-backup` > **Private** > create.
2. Close the app in PyCharm. Copy `LifeOS/database/lifeos.db` somewhere safe
   (Google Drive / phone) -- this is your original, never delete it.
3. In the `lifeos-backup` repo: Add file > Upload files > upload your local
   `lifeos.db` (file name must be exactly `lifeos.db`) > Commit.

## 2. Token (only for that one repo)
GitHub > Settings > Developer settings > Personal access tokens >
Fine-grained tokens > Generate new token:
- Repository access: **Only select repositories** > `lifeos-backup`
- Permissions > Repository permissions > **Contents: Read and write**
- Expiration: longest allowed (note the date in your calendar)
Copy the token (`github_pat_...`).

## 3. Streamlit Cloud secrets
Streamlit Cloud > your app > Settings > Secrets, paste:

    GITHUB_BACKUP_TOKEN = "github_pat_xxxxxxxx"
    GITHUB_BACKUP_REPO  = "your-github-username/lifeos-backup"
    ADMIN_EMAIL         = "your-lifeos-login-email"

Save. Push the new code to your app repo. On first start the app downloads
`lifeos.db` from the backup repo, so your old account + all data are there.
Log in with your usual email and password.

## 4. Check it works
Log in > Settings > Backup & Restore. It should say
"Automatic cloud backup is ON". Add something small, wait a minute, press
"Back up to cloud now" -- the `lifeos-backup` repo gets a new commit.
(Every backup is a commit, so old versions stay in the repo history.)

## 5. Keep the app awake (optional)
In your APP repo on GitHub: Settings > Secrets and variables > Actions >
New repository secret: name `APP_URL`, value = your app's URL.
The workflow `.github/workflows/keepalive.yml` then opens the app every 6
hours in a real browser. Test it once: Actions tab > "Keep LifeOS awake" >
Run workflow. (GitHub pauses scheduled workflows after 60 days with no
commits to the repo -- re-enable it from the Actions tab if that happens.)
Even if the app does sleep, your data is safe: it is restored on wake-up.

## Rules after the switch
- Use ONLY the deployed app from now on. Localhost has its own separate
  copy and will not sync with the deployed one.
- Never commit `lifeos.db` or secrets to the app repo.
