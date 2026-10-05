// @vitest-environment jsdom

import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { AuthDialog } from "./AuthDialog";
import { confirmCognitoSignIn, confirmCognitoSignUp, signInWithPassword, signUpWithPassword } from "../cognitoAuth";

vi.mock("../cognitoAuth", () => ({
  signInWithPassword: vi.fn(), signUpWithPassword: vi.fn(), confirmCognitoSignIn: vi.fn(),
  confirmCognitoSignUp: vi.fn(), resendCognitoSignUpCode: vi.fn(),
}));
beforeEach(() => vi.resetAllMocks());
afterEach(cleanup);

it("completes an email verification challenge before entering the workspace", async () => {
  const user = userEvent.setup();
  const onAuthenticated = vi.fn();
  signInWithPassword.mockResolvedValue({ isSignedIn: false, nextStep: { signInStep: "CONFIRM_SIGN_IN_WITH_EMAIL_CODE" } });
  confirmCognitoSignIn.mockResolvedValue({ isSignedIn: true });
  render(<AuthDialog initialMode="signIn" onClose={() => {}} onAuthenticated={onAuthenticated} />);
  await user.type(screen.getByLabelText("Email"), "candidate@example.com");
  await user.type(screen.getByLabelText("Password", { exact: true }), "example-password-1");
  await user.click(screen.getByRole("button", { name: "Log in", exact: true }));
  expect(onAuthenticated).not.toHaveBeenCalled();
  await user.type(await screen.findByLabelText("Confirmation code"), "123456");
  await user.click(screen.getByRole("button", { name: "Continue" }));
  expect(confirmCognitoSignIn).toHaveBeenCalledWith("123456");
  expect(onAuthenticated).toHaveBeenCalledTimes(1);
});

it("lets a new account retry an incorrect confirmation code", async () => {
  const user = userEvent.setup();
  const onAuthenticated = vi.fn();
  signUpWithPassword.mockResolvedValue({ isSignUpComplete: false });
  confirmCognitoSignUp.mockRejectedValueOnce({ name: "CodeMismatchException" }).mockResolvedValueOnce({ isSignUpComplete: true });
  signInWithPassword.mockResolvedValue({ isSignedIn: true });
  render(<AuthDialog initialMode="signUp" onClose={() => {}} onAuthenticated={onAuthenticated} />);
  await user.type(screen.getByLabelText("Email"), "candidate@example.com");
  await user.type(screen.getByLabelText("Password", { exact: true }), "example-password-1");
  await user.type(screen.getByLabelText("Confirm password"), "example-password-1");
  await user.click(screen.getByRole("button", { name: "Create account" }));
  const code = await screen.findByLabelText("Confirmation code");
  await user.type(code, "000000");
  await user.click(screen.getByRole("button", { name: "Continue" }));
  expect((await screen.findByRole("alert")).textContent).toContain("That verification code is not correct.");
  expect(onAuthenticated).not.toHaveBeenCalled();
  await user.clear(code);
  await user.type(code, "123456");
  await user.click(screen.getByRole("button", { name: "Continue" }));
  expect(confirmCognitoSignUp).toHaveBeenLastCalledWith("candidate@example.com", "123456");
  expect(onAuthenticated).toHaveBeenCalledTimes(1);
});
