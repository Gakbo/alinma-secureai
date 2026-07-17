"""
Tests for backend/app/email_utils.py

Covers:
  - check_email_config() reports missing credentials correctly
  - check_email_config() passes when all required vars are set
  - check_email_config() warns when APP_URL is still the localhost default
  - send_password_reset_email() falls back to console when SMTP is unconfigured
  - send_password_reset_email() calls smtplib.SMTP and sends when configured
  - send_password_reset_email() raises on SMTP errors (does not swallow them)
"""
import smtplib
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _patched_env(env: dict):
    """
    Return a context manager that patches os.environ for the duration of a
    with-block, clearing all existing vars and substituting only `env`.
    Use inside each test so the patch is active when the function under test
    runs.
    """
    return patch.dict("os.environ", env, clear=True)


def _email_mod():
    """Return the email_utils module (already imported by the test process)."""
    import app.email_utils as mod
    return mod


# ---------------------------------------------------------------------------
# check_email_config
# ---------------------------------------------------------------------------

class TestCheckEmailConfig:
    def test_missing_both_credentials(self):
        with _patched_env({}):
            result = _email_mod().check_email_config()
        assert result["configured"] is False
        assert "SMTP_USER" in result["missing"]
        assert "SMTP_PASS" in result["missing"]

    def test_missing_only_smtp_pass(self):
        with _patched_env({"SMTP_USER": "user@example.com"}):
            result = _email_mod().check_email_config()
        assert result["configured"] is False
        assert "SMTP_PASS" in result["missing"]
        assert "SMTP_USER" not in result["missing"]

    def test_configured_when_both_set(self):
        env = {
            "SMTP_USER": "user@example.com",
            "SMTP_PASS": "secret",
            "APP_URL": "https://my-app.replit.app",
        }
        with _patched_env(env):
            result = _email_mod().check_email_config()
        assert result["configured"] is True
        assert result["missing"] == []

    def test_warns_when_app_url_is_localhost_default(self):
        """APP_URL absent → default localhost → should produce a warning."""
        env = {
            "SMTP_USER": "user@example.com",
            "SMTP_PASS": "secret",
            # APP_URL intentionally absent → defaults to http://localhost:5173
        }
        with _patched_env(env):
            result = _email_mod().check_email_config()
        assert result["configured"] is True
        assert any("APP_URL" in w for w in result["warnings"])

    def test_no_warnings_when_fully_configured(self):
        env = {
            "SMTP_USER": "user@example.com",
            "SMTP_PASS": "secret",
            "SMTP_FROM": "noreply@example.com",
            "APP_URL": "https://my-app.replit.app",
        }
        with _patched_env(env):
            result = _email_mod().check_email_config()
        assert result["configured"] is True
        assert result["warnings"] == []


# ---------------------------------------------------------------------------
# send_password_reset_email — dev fallback (no SMTP)
# ---------------------------------------------------------------------------

class TestSendPasswordResetEmailDevFallback:
    def test_prints_link_when_no_credentials(self, capsys):
        with _patched_env({}):
            _email_mod().send_password_reset_email("user@example.com", "tok123")
        captured = capsys.readouterr()
        assert "tok123" in captured.out
        assert "user@example.com" in captured.out

    def test_does_not_raise_when_no_credentials(self):
        with _patched_env({}):
            # Must not raise even though SMTP is not configured
            _email_mod().send_password_reset_email("user@example.com", "tok123")

    def test_reset_link_contains_token(self, capsys):
        env = {"APP_URL": "https://my-app.replit.app"}
        with _patched_env(env):
            _email_mod().send_password_reset_email("u@example.com", "mytoken")
        captured = capsys.readouterr()
        assert "https://my-app.replit.app/reset-password?token=mytoken" in captured.out


# ---------------------------------------------------------------------------
# send_password_reset_email — SMTP path
# ---------------------------------------------------------------------------

class TestSendPasswordResetEmailSmtp:
    def _env(self, **extra):
        base = {
            "SMTP_USER": "sender@example.com",
            "SMTP_PASS": "secret",
            "SMTP_HOST": "smtp.example.com",
            "SMTP_PORT": "587",
            "SMTP_FROM": "noreply@example.com",
            "APP_URL": "https://my-app.replit.app",
        }
        base.update(extra)
        return base

    def test_sends_via_smtp_when_configured(self):
        mock_server = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_server)
        mock_ctx.__exit__ = MagicMock(return_value=False)

        with _patched_env(self._env()), patch("smtplib.SMTP") as mock_smtp_cls:
            mock_smtp_cls.return_value = mock_ctx
            _email_mod().send_password_reset_email("recipient@example.com", "tok456")

        mock_smtp_cls.assert_called_once_with("smtp.example.com", 587, timeout=10)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("sender@example.com", "secret")
        mock_server.sendmail.assert_called_once()
        # Verify recipient is in the sendmail call
        call_args = mock_server.sendmail.call_args
        assert "recipient@example.com" in call_args[0][1]

    def test_reset_link_in_email_body(self):
        captured_messages = []
        mock_server = MagicMock()

        def capture_sendmail(from_addr, to_addrs, msg_str):
            captured_messages.append(msg_str)

        mock_server.sendmail.side_effect = capture_sendmail
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_server)
        mock_ctx.__exit__ = MagicMock(return_value=False)

        with _patched_env(self._env()), patch("smtplib.SMTP") as mock_smtp_cls:
            mock_smtp_cls.return_value = mock_ctx
            _email_mod().send_password_reset_email("recipient@example.com", "tok789")

        assert len(captured_messages) == 1
        assert "tok789" in captured_messages[0]
        assert "https://my-app.replit.app/reset-password?token=tok789" in captured_messages[0]

    def test_raises_on_smtp_error(self):
        mock_server = MagicMock()
        mock_server.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Bad credentials")
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_server)
        mock_ctx.__exit__ = MagicMock(return_value=False)

        raised = False
        with _patched_env(self._env()), patch("smtplib.SMTP") as mock_smtp_cls:
            mock_smtp_cls.return_value = mock_ctx
            try:
                _email_mod().send_password_reset_email("recipient@example.com", "tok")
            except smtplib.SMTPAuthenticationError:
                raised = True

        assert raised, "Expected SMTPAuthenticationError to be raised"
