/**
 * Email verification page.
 *
 * Shown after registration. Instructs the user to check their email
 * and provides a button to resend the verification email.
 */

"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { verifyEmail } from "@/lib/firebase/auth";
import { useAuth } from "@/hooks/use-auth";

export default function VerifyEmailPage() {
  const [isResending, setIsResending] = useState(false);
  const [resent, setResent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { user, isAuthenticated } = useAuth();
  const router = useRouter();

  if (isAuthenticated && user?.emailVerified) {
    router.replace("/dashboard");
    return null;
  }

  async function handleResend() {
    setIsResending(true);
    setError(null);

    try {
      await verifyEmail();
      setResent(true);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to resend verification email"
      );
    } finally {
      setIsResending(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-xl font-semibold text-foreground">
          Verify your email
        </h2>
        <p className="mt-2 text-sm text-muted-foreground">
          We&apos;ve sent a verification link to{" "}
          <strong>{user?.email ?? "your email"}</strong>.
        </p>
        <p className="mt-2 text-sm text-muted-foreground">
          Click the link in the email to activate your account.
        </p>
      </div>

      {error && (
        <div
          role="alert"
          className="rounded-md bg-destructive/10 p-3 text-sm text-destructive"
        >
          {error}
        </div>
      )}

      {resent && (
        <div
          role="status"
          className="rounded-md bg-primary/10 p-3 text-sm text-primary"
        >
          Verification email resent successfully.
        </div>
      )}

      <button
        type="button"
        onClick={handleResend}
        disabled={isResending}
        className="w-full rounded-md border border-input bg-background px-4 py-2 text-sm font-medium text-foreground hover:bg-accent disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isResending ? "Sending..." : "Resend verification email"}
      </button>

      <Link
        href="/login"
        className="block w-full rounded-md bg-primary px-4 py-2 text-center text-sm font-medium text-primary-foreground hover:bg-primary/90"
      >
        Back to sign in
      </Link>
    </div>
  );
}
