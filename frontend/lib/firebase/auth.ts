/**
 * Firebase Authentication client-side operations.
 *
 * Wraps Firebase Auth SDK for sign-in, sign-up, sign-out, and token management.
 * All functions are async and handle errors in a structured way.
 */

import {
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signInWithPopup,
  GoogleAuthProvider,
  signOut,
  sendPasswordResetEmail,
  sendEmailVerification,
  type User as FirebaseUser,
  type UserCredential,
} from "firebase/auth";
import { getFirebaseAuth } from "./config";

const googleProvider = new GoogleAuthProvider();
googleProvider.addScope("email");
googleProvider.addScope("profile");

export interface AuthResult {
  user: FirebaseUser;
  idToken: string;
}

export async function signInWithEmail(
  email: string,
  password: string
): Promise<AuthResult> {
  const auth = getFirebaseAuth();
  const credential: UserCredential = await signInWithEmailAndPassword(
    auth,
    email,
    password
  );
  const idToken = await credential.user.getIdToken();
  return { user: credential.user, idToken };
}

export async function signUpWithEmail(
  email: string,
  password: string
): Promise<AuthResult> {
  const auth = getFirebaseAuth();
  const credential: UserCredential = await createUserWithEmailAndPassword(
    auth,
    email,
    password
  );
  const idToken = await credential.user.getIdToken();
  return { user: credential.user, idToken };
}

export async function signInWithGoogle(): Promise<AuthResult> {
  const auth = getFirebaseAuth();
  const credential: UserCredential = await signInWithPopup(
    auth,
    googleProvider
  );
  const idToken = await credential.user.getIdToken();
  return { user: credential.user, idToken };
}

export async function signOutUser(): Promise<void> {
  const auth = getFirebaseAuth();
  await signOut(auth);
}

export async function resetPassword(email: string): Promise<void> {
  const auth = getFirebaseAuth();
  await sendPasswordResetEmail(auth, email);
}

export async function verifyEmail(): Promise<void> {
  const auth = getFirebaseAuth();
  const user = auth.currentUser;
  if (!user) {
    throw new Error("No authenticated user");
  }
  await sendEmailVerification(user);
}

export async function getIdToken(): Promise<string | null> {
  const auth = getFirebaseAuth();
  const user = auth.currentUser;
  if (!user) return null;
  return user.getIdToken();
}

export function getCurrentUser(): FirebaseUser | null {
  const auth = getFirebaseAuth();
  return auth.currentUser;
}
