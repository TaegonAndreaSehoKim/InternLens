import { Amplify } from "aws-amplify";
import {
  confirmSignIn,
  confirmSignUp,
  fetchAuthSession,
  fetchUserAttributes,
  getCurrentUser,
  resendSignUpCode,
  signIn,
  signOut,
  signUp
} from "aws-amplify/auth";

let configuredPool = "";

function configureCognitoAuth({ userPoolId, userPoolClientId }) {
  if (!userPoolId || !userPoolClientId) {
    return false;
  }

  const poolKey = `${userPoolId}:${userPoolClientId}`;
  if (configuredPool === poolKey) {
    return true;
  }

  Amplify.configure({
    Auth: {
      Cognito: {
        userPoolId,
        userPoolClientId,
        loginWith: { email: true },
        signUpVerificationMethod: "code",
        userAttributes: { email: { required: true } }
      }
    }
  });
  configuredPool = poolKey;
  return true;
}

async function currentCognitoSession() {
  const user = await getCurrentUser();
  const [session, attributes] = await Promise.all([
    fetchAuthSession(),
    fetchUserAttributes().catch(() => ({}))
  ]);
  const accessToken = session.tokens?.accessToken?.toString() ?? "";

  if (!accessToken) {
    throw new Error("Your session could not be restored. Please log in again.");
  }

  return {
    accessToken,
    email: attributes.email ?? user.signInDetails?.loginId ?? user.username
  };
}

function signInWithPassword(email, password) {
  return signIn({ username: email, password });
}

function signUpWithPassword(email, password) {
  return signUp({
    username: email,
    password,
    options: {
      userAttributes: { email }
    }
  });
}

function confirmCognitoSignUp(email, confirmationCode) {
  return confirmSignUp({ username: email, confirmationCode });
}

function resendCognitoSignUpCode(email) {
  return resendSignUpCode({ username: email });
}

function confirmCognitoSignIn(challengeResponse) {
  return confirmSignIn({ challengeResponse });
}

function signOutCognito() {
  return signOut();
}

export {
  configureCognitoAuth,
  confirmCognitoSignIn,
  confirmCognitoSignUp,
  currentCognitoSession,
  resendCognitoSignUpCode,
  signInWithPassword,
  signOutCognito,
  signUpWithPassword
};
