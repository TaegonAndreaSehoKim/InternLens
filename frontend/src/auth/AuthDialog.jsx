import { useState } from "react";
import {
  confirmCognitoSignIn,
  confirmCognitoSignUp,
  resendCognitoSignUpCode,
  signInWithPassword,
  signUpWithPassword
} from "../cognitoAuth";

function authErrorMessage(error) {
  const messages = {
    CodeMismatchException: "That verification code is not correct.",
    ExpiredCodeException: "That verification code has expired. Request a new code.",
    InvalidPasswordException: "Choose a password that meets the account requirements.",
    LimitExceededException: "Too many attempts. Please wait a moment and try again.",
    NotAuthorizedException: "The email or password is incorrect.",
    PasswordResetRequiredException: "This account needs a password reset before it can log in.",
    TooManyRequestsException: "Too many attempts. Please wait a moment and try again.",
    UserNotFoundException: "The email or password is incorrect.",
    UsernameExistsException: "An account with this email already exists. Log in instead."
  };
  return messages[error?.name] ?? error?.message ?? "Authentication failed. Please try again.";
}

function AuthDialog({ initialMode, onClose, onAuthenticated }) {
  const [mode, setMode] = useState(initialMode);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [challengeResponse, setChallengeResponse] = useState("");
  const [challengeKind, setChallengeKind] = useState("code");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  function switchMode(nextMode) {
    setMode(nextMode);
    setMessage("");
    setError("");
    setChallengeResponse("");
  }

  async function finishSignIn(result) {
    const step = result.nextStep?.signInStep;
    if (result.isSignedIn || step === "DONE") {
      await onAuthenticated();
      return;
    }
    if (step === "CONFIRM_SIGN_UP") {
      setMode("confirmSignUp");
      setMessage("Enter the confirmation code sent to your email.");
      return;
    }
    if (step === "CONFIRM_SIGN_IN_WITH_NEW_PASSWORD_REQUIRED") {
      setChallengeKind("password");
      setMode("confirmSignIn");
      setMessage("Choose a new password to finish signing in.");
      return;
    }
    if (["CONFIRM_SIGN_IN_WITH_EMAIL_CODE", "CONFIRM_SIGN_IN_WITH_SMS_CODE", "CONFIRM_SIGN_IN_WITH_TOTP_CODE"].includes(step)) {
      setChallengeKind("code");
      setMode("confirmSignIn");
      setMessage("Enter the verification code to finish signing in.");
      return;
    }
    throw new Error("This account requires an authentication step that is not supported yet.");
  }

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    try {
      if (mode === "signIn") {
        await finishSignIn(await signInWithPassword(email.trim(), password));
      } else if (mode === "signUp") {
        if (password !== confirmPassword) {
          throw new Error("Passwords do not match.");
        }
        const result = await signUpWithPassword(email.trim(), password);
        if (result.isSignUpComplete || result.nextStep?.signUpStep === "DONE") {
          await finishSignIn(await signInWithPassword(email.trim(), password));
        } else {
          setMode("confirmSignUp");
          setMessage("We sent a confirmation code to your email.");
        }
      } else if (mode === "confirmSignUp") {
        await confirmCognitoSignUp(email.trim(), challengeResponse.trim());
        await finishSignIn(await signInWithPassword(email.trim(), password));
      } else {
        await finishSignIn(await confirmCognitoSignIn(challengeResponse));
      }
    } catch (authError) {
      setError(authErrorMessage(authError));
    } finally {
      setBusy(false);
    }
  }

  async function resendCode() {
    setBusy(true);
    setError("");
    try {
      await resendCognitoSignUpCode(email.trim());
      setMessage("A new confirmation code was sent to your email.");
    } catch (authError) {
      setError(authErrorMessage(authError));
    } finally {
      setBusy(false);
    }
  }

  const isSignUp = mode === "signUp";
  const isConfirmation = mode === "confirmSignUp" || mode === "confirmSignIn";
  const title = mode === "signIn" ? "Log in" : isSignUp ? "Create your account" : "Confirm your account";

  return (
    <div className="auth-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="auth-dialog" role="dialog" aria-modal="true" aria-labelledby="auth-dialog-title">
        <div className="auth-dialog-heading">
          <div>
            <p className="eyebrow">InternLens account</p>
            <h2 id="auth-dialog-title">{title}</h2>
          </div>
          <button className="auth-close" type="button" onClick={onClose} aria-label="Close account form">
            Close
          </button>
        </div>

        <form className="auth-form" onSubmit={submit}>
          {mode !== "confirmSignIn" && (
            <label>
              Email
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                autoComplete="email"
                placeholder="you@example.com"
                disabled={mode === "confirmSignUp"}
                required
                autoFocus
              />
            </label>
          )}

          {(mode === "signIn" || isSignUp) && (
            <label>
              Password
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete={isSignUp ? "new-password" : "current-password"}
                placeholder="Enter your password"
                required
              />
            </label>
          )}

          {isSignUp && (
            <label>
              Confirm password
              <input
                type="password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                autoComplete="new-password"
                placeholder="Enter your password again"
                required
              />
            </label>
          )}

          {isConfirmation && (
            <label>
              {challengeKind === "password" ? "New password" : "Confirmation code"}
              <input
                type={challengeKind === "password" ? "password" : "text"}
                inputMode={challengeKind === "password" ? undefined : "numeric"}
                value={challengeResponse}
                onChange={(event) => setChallengeResponse(event.target.value)}
                autoComplete={challengeKind === "password" ? "new-password" : "one-time-code"}
                placeholder={challengeKind === "password" ? "Choose a new password" : "Enter code"}
                required
                autoFocus
              />
            </label>
          )}

          {message && <p className="auth-message" role="status">{message}</p>}
          {error && <p className="auth-error" role="alert">{error}</p>}

          <button className="primary-action auth-submit" type="submit" disabled={busy}>
            {busy ? "Please wait..." : mode === "signIn" ? "Log in" : isSignUp ? "Create account" : "Continue"}
          </button>
        </form>

        {mode === "confirmSignUp" ? (
          <button className="auth-switch" type="button" onClick={resendCode} disabled={busy}>
            Send a new code
          </button>
        ) : !isConfirmation ? (
          <p className="auth-alternate">
            {isSignUp ? "Already have an account?" : "New to InternLens?"}
            <button type="button" onClick={() => switchMode(isSignUp ? "signIn" : "signUp")}>
              {isSignUp ? "Log in" : "Create an account"}
            </button>
          </p>
        ) : null}
      </section>
    </div>
  );
}

export { AuthDialog, authErrorMessage };
