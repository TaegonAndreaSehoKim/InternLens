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
  accessTokenForUser(session, user.userId);

  return {
    userId: user.userId,
    email: attributes.email ?? user.signInDetails?.loginId ?? user.username
  };
}

function accessTokenForUser(session, userId) {
  const token = session.tokens?.accessToken;
  if (!userId || token?.payload?.sub !== userId || !token.toString()) {
    throw Object.assign(new Error("Your session ended or changed. Please log in again."), { status: 401 });
  }
  return token.toString();
}

async function currentCognitoAccessToken(userId, { forceRefresh = false } = {}) {
  const session = await fetchAuthSession({ forceRefresh });
  return accessTokenForUser(session, userId);
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
  currentCognitoAccessToken,
  currentCognitoSession,
  resendCognitoSignUpCode,
  signInWithPassword,
  signOutCognito,
  signUpWithPassword
};
