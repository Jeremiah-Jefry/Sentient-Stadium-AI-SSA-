/**
 * Layout wrapper for all authentication pages.
 *
 * Provides a centered card layout with the StadiumMind branding
 * for login, register, and password reset pages.
 */

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4 py-12">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center">
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            StadiumMind OS
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            FIFA World Cup 2026 Volunteer Platform
          </p>
        </div>
        <div className="rounded-lg border bg-card p-8 shadow-sm">
          {children}
        </div>
      </div>
    </div>
  );
}
