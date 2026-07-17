# SMTP / Email Setup for Production

Alinma SecureAI sends two types of transactional email:

- **Password-reset emails** — triggered when a user requests a reset link
- **Fraud-alert emails** — triggered when a high-severity fraud event is detected

Both are sent via `backend/app/email_utils.py`.  In development the emails
are printed to the server console (no credentials needed).  In production you
must supply real SMTP credentials.

---

## Required environment variables (set in `backend/.env` or your deployment platform's secrets)

| Variable name | Description | Example |
|-------------|-------------|---------|
| `SMTP_USER` | SMTP login username (usually the sender address) | `alerts@alinma.com` |
| `SMTP_PASS` | SMTP password or app-specific password | *(keep private)* |

## Optional variables (have sensible defaults shown)

| Variable name | Default | Notes |
|-------------|---------|-------|
| `SMTP_HOST` | `smtp.gmail.com` | Change to your provider's host, e.g. `smtp.resend.com` |
| `SMTP_PORT` | `587` | Use `587` for STARTTLS, `465` for SSL |
| `SMTP_FROM` | Same as `SMTP_USER` | Override to show a branded From address |
| `APP_URL` | `http://localhost:5173` | **Must be set** to your production URL, e.g. `https://secureai.example.com` — this is embedded in the reset-link inside every email |

---

## Gmail setup (recommended for small deployments)

1. Enable 2-Step Verification on your Google account.
2. Go to **Google Account → Security → App passwords**.
3. Create an app password (name it "Alinma SecureAI").
4. Set `SMTP_USER` to your Gmail address and `SMTP_PASS` to the generated
   16-character app password.
5. Leave `SMTP_HOST` and `SMTP_PORT` at defaults (`smtp.gmail.com` / `587`).

## Resend setup (recommended for transactional volume)

1. Create an account at [resend.com](https://resend.com) and verify your domain.
2. Generate an API key.
3. Set:
   - `SMTP_HOST` → `smtp.resend.com`
   - `SMTP_PORT` → `587`
   - `SMTP_USER` → `resend`  (literal string, not your email)
   - `SMTP_PASS` → your Resend API key
   - `SMTP_FROM` → `noreply@yourdomain.com` (must be a verified sender)

---

## Verifying the configuration

The backend logs the email-config status on every startup.  Look for lines
like:

```
INFO  Email: SMTP configured — host=smtp.gmail.com port=587 from=alerts@alinma.com app_url=https://secureai.example.com
```

or a warning if credentials are missing:

```
WARNING Email: SMTP not configured — missing env vars: SMTP_USER, SMTP_PASS.
        Password-reset and fraud-alert emails will NOT be delivered to real users.
        In development, reset links are printed to this console instead.
```

---

## How the fallback works

When `SMTP_USER` / `SMTP_PASS` are absent the app does **not** crash —
instead it prints the reset link to the server console.  This is intentional
for development but **must not** be relied on in production.
