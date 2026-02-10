[README.md](https://github.com/user-attachments/files/25061112/README.md)
# Strava Summit Grids (Streamlit Dashboard)

This project builds a **Streamlit dashboard** that visualizes “summit grids” for common Colorado and New Hampshire peaks. Included are my home peaks in Boulder, Colorado 14ers, and New Hampshire 4kers.

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
- A terminal (Windows PowerShell is fine)

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
cd strava_lab
```

Replace `<YOUR_GITHUB_REPO_URL>` with the repo URL from GitHub.

---

## Step 1 — Open a terminal in the project folder

### Windows (PowerShell)
1. Open File Explorer
2. Navigate to the project folder (the one containing `streamlit_app.py`)
3. Click the address bar, type `powershell`, press Enter

---

## Step 2 — Create and activate a virtual environment

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

---

## Step 3 — Install dependencies

```powershell
pip install -r requirements.txt
```

If that fails:
```powershell
pip install -e .
pip install streamlit
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

```powershell
Copy-Item .env.example .env
```

Edit `.env`:
```env
STRAVA_CLIENT_ID=your_client_id_here
STRAVA_CLIENT_SECRET=your_client_secret_here
STRAVA_REFRESH_TOKEN=your_refresh_token_here
```

Note: you'll only be adding the first two items here. To find your refresh token, read on.
---

## Step 6 — Generate a Strava refresh token

1. Set **Authorization Callback Domain** to:
```
localhost
```

2. Open:
```
https://www.strava.com/oauth/authorize?client_id=YOUR_CLIENT_ID&response_type=code&redirect_uri=http://localhost&approval_prompt=force&scope=read,activity:read_all
```

3. Approve access and copy the `code=...` value.

Exchange it:
```powershell
curl -X POST https://www.strava.com/oauth/token `
  -d client_id=YOUR_CLIENT_ID `
  -d client_secret=YOUR_CLIENT_SECRET `
  -d code=YOUR_CODE `
  -d grant_type=authorization_code
```

Copy `refresh_token` into `.env`.

---

## Step 7 — Pull your Strava activities

```powershell
python scripts\pull_activities.py
```

---

## Step 8 — Build the processed dataset

```powershell
python scripts\build_dataset.py
```

---

## Step 9 — Run the Streamlit dashboard

```powershell
streamlit run streamlit_app.py
```

Open the local URL shown in the terminal.

---

## Using the dashboard

- By default, the dashboard starts off only populating peaks with valid summits.
- You can see your overall activity grid at the top.
- Select your desired states (only Colorado and New Hampshire currently available) and desired peaks
- Darker green = more summit touches

---

## Security notes

Never commit:
- `.env`
- `data/raw/*`
- API tokens or secrets


