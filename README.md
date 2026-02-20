# Strava Summit Grids (Streamlit Dashboard)

This project builds a **Streamlit dashboard** that visualizes “summit grids” for any peak in the US.

A *summit grid* is a calendar-style heatmap:

- **Rows** = months (Jan–Dec)  
- **Columns** = day of month (1–31)  
- **Cell value** = number of summit touches on that month/day **across all years**  
- **Invalid dates** (e.g., April 31) are **blank and gray** and do not count

---

## What this project does (plain English)

1. Pulls your activities from **Strava** using the Strava API  
2. Builds a local dataset of your activities  
3. Detects summit visits by decoding GPS polylines  
4. Displays a clean, interactive **calendar heatmap** in Streamlit  

You end up with a dashboard you can open anytime to track your progress toward completing a summit on every calendar day.

---

## Requirements

### You need
- A computer (Windows, macOS, or Linux)
- Internet access
- A **Strava account**
- **Python 3.10 or newer**
- A terminal (**PowerShell** on Windows, **Terminal** on macOS)

### You will create
- A Strava API application (free)
- A local `.env` file with Strava credentials

---

## Step 0 — Download or clone the repository

### Option A: Download ZIP (simplest)
1. Click **Code → Download ZIP** on GitHub
2. Unzip the folder somewhere easy to find (e.g., Desktop)

### Option B: Clone with Git
```bash
git clone <YOUR_GITHUB_REPO_URL>
cd mtn-grid
```

Replace `<YOUR_GITHUB_REPO_URL>` with the repo URL from GitHub.

---

## Step 1 — Open a terminal in the project folder

### Windows (PowerShell)
1. Open File Explorer
2. Navigate to the project folder (the one containing `streamlit_app.py`)
3. Click the address bar, type `powershell`, press Enter

### macOS (Terminal)
1. Open **Terminal**
2. `cd` into the project folder (example if it’s on your Desktop):
```bash
cd ~/Desktop/mtn_grid
```
> Tip: you can also drag the folder from Finder into the Terminal window to paste its path.

---

## Step 2 — Create and activate a virtual environment

### Windows (PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run:
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then activate again:
```powershell
.\.venv\Scripts\Activate.ps1
```

### macOS (Terminal)
Create the venv:
```bash
python3 -m venv .venv
```

Activate it:
```bash
source .venv/bin/activate
```

You should now see `(.venv)` at the start of your terminal prompt.

---

## Step 3 — Install dependencies

### Windows / macOS
```bash
pip install -r requirements.txt
pip install -e .
```

---

## Step 4 — Create a Strava API application

1. Go to **Strava → Settings → My API Application**
2. Create a new application (name/logo do not matter)
3. Copy:
   - **Client ID**
   - **Client Secret**

---

## Step 5 — Create your `.env` file

### Windows (PowerShell)
```powershell
Copy-Item .env.example .env
```

### macOS (Terminal)
```bash
cp .env.example .env
```

Edit `.env` (any editor is fine). For macOS, `nano` is the simplest:
```bash
nano .env
```

Add:
```env
STRAVA_CLIENT_ID=your_client_id_here
STRAVA_CLIENT_SECRET=your_client_secret_here
STRAVA_REFRESH_TOKEN=your_refresh_token_here
```

Note: you'll only be adding `STRAVA_CLIENT_ID` and `STRAVA_CLIENT_SECRET` here initially. Read on for `STRAVA_REFRESH_TOKEN`.

---

## Step 6 — Generate a Strava refresh token

1. Click **EDIT** on Strava under **My API Application**, then set **Authorization Callback Domain** to:
```
localhost
```

2. Open the following link after pasting your client ID in place of `YOUR_CLIENT_ID`:
```
https://www.strava.com/oauth/authorize?client_id=YOUR_CLIENT_ID&response_type=code&redirect_uri=http://localhost&approval_prompt=force&scope=read,activity:read_all
```

3. Approve access and copy the `code=...` value from the redirected URL.

### Exchange the code for tokens

#### macOS (Terminal) — paste as ONE command
```bash
curl -X POST https://www.strava.com/oauth/token   -d client_id=YOUR_CLIENT_ID   -d client_secret=YOUR_CLIENT_SECRET   -d code=YOUR_CODE   -d grant_type=authorization_code
```

#### Windows (PowerShell)
```powershell
curl -X POST https://www.strava.com/oauth/token `
  -d client_id=YOUR_CLIENT_ID `
  -d client_secret=YOUR_CLIENT_SECRET `
  -d code=YOUR_CODE `
  -d grant_type=authorization_code
```

Copy `refresh_token` from the response into `.env`.

---

## Step 7 — Pull your Strava activities

### Windows (PowerShell)
```powershell
python scripts\pull_activities.py
```

### macOS (Terminal)
```bash
python -m scripts.pull_activities
```

---

## Step 8 — Build the processed dataset

### Windows (PowerShell)
```powershell
python scripts\build_dataset.py
```

### macOS (Terminal)
```bash
python -m scripts.build_dataset
```

---

## Step 9 — Run the Streamlit dashboard

### Windows / macOS
```bash
streamlit run streamlit_app.py
```

Open the local URL shown in the terminal.

---

## Using the dashboard

- By default, the dashboard starts off only populating peaks with valid summits.
- You can see your overall activity grid at the top.
- Select your desired states and desired peaks.
- Select your desired summit threshold.
- Darker green = more summit touches.

---

## Security notes

Never commit:
- `.env`
- `data/raw/*`
- API tokens or secrets
