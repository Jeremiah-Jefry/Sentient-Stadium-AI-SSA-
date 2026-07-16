# StadiumMind OS - IAM Module Architecture

## Folder Structure

```
backend/
├── pyproject.toml                          # Python dependencies & tooling
├── .env.example                            # Environment variable template
├── alembic.ini                             # Alembic migration config
├── alembic/
│   ├── env.py                              # Async migration runner
│   ├── script.py.mako                      # Migration template
│   └── versions/
│       └── 001_initial.py                  # Initial schema migration
└── app/
    ├── __init__.py
    ├── main.py                             # FastAPI application factory
    ├── config.py                           # Pydantic settings (env-based)
    ├── shared/
    │   ├── __init__.py
    │   ├── database.py                     # Async SQLAlchemy engine & sessions
    │   ├── result.py                       # Typed Result<T> monad
    │   ├── exceptions.py                   # Domain exception hierarchy
    │   ├── models/
    │   │   ├── __init__.py
    │   │   └── base.py                     # SQLAlchemy base, mixins (UUID, timestamps, soft-delete)
    │   └── utils/
    │       ├── __init__.py
    │       └── sanitization.py             # Input sanitization & prompt injection detection
    └── features/
        └── auth/
            ├── __init__.py
            ├── models/
            │   ├── __init__.py
            │   ├── user.py                 # User entity
            │   ├── role.py                 # Role entity
            │   ├── permission.py           # Permission entity
            │   ├── user_role.py            # User-Role junction
            │   ├── role_permission.py      # Role-Permission junction
            │   ├── session.py              # Session tracking
            │   └── audit_log.py            # Immutable audit trail
            ├── dto/
            │   ├── __init__.py
            │   ├── auth_requests.py        # Inbound auth request schemas
            │   ├── auth_responses.py       # Outbound auth response schemas
            │   ├── user_requests.py        # Inbound user management requests
            │   └── user_responses.py       # Outbound user management responses
            ├── repositories/
            │   ├── __init__.py
            │   ├── user_repository.py      # User data access
            │   ├── role_repository.py      # Role/permission data access
            │   ├── session_repository.py   # Session data access
            │   └── audit_repository.py     # Audit log data access
            ├── services/
            │   ├── __init__.py
            │   ├── auth_service.py         # Authentication orchestration
            │   ├── firebase_service.py     # Firebase Admin SDK integration
            │   ├── token_service.py        # JWT & refresh token management
            │   ├── rbac_service.py         # RBAC permission resolution
            │   ├── session_service.py      # Session lifecycle management
            │   └── audit_service.py        # Security event recording
            ├── api/
            │   ├── __init__.py
            │   ├── router.py               # Route aggregation
            │   ├── deps.py                 # FastAPI dependency injection
            │   ├── auth_routes.py          # Auth endpoints
            │   ├── user_routes.py          # User profile endpoints
            │   ├── admin_routes.py         # Admin management endpoints
            │   ├── error_handlers.py       # Exception → HTTP mapping
            │   └── middleware.py           # Security headers, rate limiting
            └── tests/
                └── __init__.py

frontend/
├── package.json                            # Node.js dependencies
├── tsconfig.json                           # TypeScript strict config
├── next.config.ts                          # Next.js configuration
├── tailwind.config.ts                      # Tailwind CSS theme
├── postcss.config.mjs                      # PostCSS plugins
├── .env.local.example                      # Frontend env template
├── app/
│   ├── layout.tsx                          # Root layout with AuthProvider
│   ├── globals.css                         # Dark theme CSS variables
│   ├── (auth)/
│   │   ├── layout.tsx                      # Auth page card layout
│   │   ├── login/page.tsx                  # Login page
│   │   ├── register/page.tsx               # Registration page
│   │   ├── forgot-password/page.tsx        # Password reset page
│   │   └── verify-email/page.tsx           # Email verification page
│   └── dashboard/
│       └── page.tsx                        # Protected dashboard
├── components/
│   └── auth/
│       ├── protected-route.tsx             # Auth guard wrapper
│       └── role-guard.tsx                  # RBAC guard wrapper
├── contexts/
│   └── auth-context.tsx                    # Global auth state
├── hooks/
│   ├── use-auth.ts                         # Auth context hook
│   └── use-rbac.ts                         # RBAC context hook
├── lib/
│   ├── firebase/
│   │   ├── config.ts                       # Firebase client init
│   │   └── auth.ts                         # Firebase auth operations
│   └── auth/
│       └── api-client.ts                   # Typed API client
└── types/
    └── auth.ts                             # Shared TypeScript types
```

## Database Schema

### Entity Relationship Diagram

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│    users     │────<│  user_roles   │>────│    roles     │
│─────────────│     │──────────────│     │─────────────│
│ id (UUID PK)│     │ user_id (FK) │     │ id (UUID PK)│
│ firebase_uid│     │ role_id (FK) │     │ name        │
│ email       │     │ venue_id     │     │ display_name│
│ display_name│     │ event_id     │     │ description │
│ photo_url   │     │ assigned_by  │     │ scope       │
│ phone_number│     │ expires_at   │     │ is_default  │
│ auth_provider│    │ created_at   │     │ deleted_at  │
│ email_verified│   │ updated_at   │     │ created_at  │
│ status      │     └──────────────┘     │ updated_at  │
│ failed_attempts│                       └──────┬──────┘
│ locked_until │                                │
│ last_login_at│                       ┌────────┴────────┐
│ password_hash│                       │ role_permissions │
│ deleted_at   │                       │────────────────│
│ created_at   │                       │ role_id (FK)    │
│ updated_at   │                       │ permission_id(FK)│
└──────┬───────┘                       │ created_at      │
       │                               │ updated_at      │
       │                               └────────┬────────┘
       │                                        │
       │                               ┌────────┴────────┐
       │                               │   permissions    │
       │                               │────────────────│
       │                               │ id (UUID PK)    │
       │                               │ name            │
       │                               │ resource        │
       │                               │ action          │
       │                               │ description     │
       │                               │ deleted_at      │
       │                               │ created_at      │
       │                               │ updated_at      │
       │                               └─────────────────┘
       │
       ├──────────────────┐
       │                  │
┌──────┴───────┐  ┌───────┴──────┐
│ user_sessions │  │  audit_logs   │
│──────────────│  │──────────────│
│ id (UUID PK) │  │ id (UUID PK) │
│ user_id      │  │ user_id      │
│ refresh_hash │  │ event_type   │
│ fingerprint  │  │ ip_address   │
│ ip_address   │  │ user_agent   │
│ user_agent   │  │ resource_type│
│ device_info  │  │ resource_id  │
│ is_revoked   │  │ details      │
│ revoke_reason│  │ risk_score   │
│ expires_at   │  │ session_id   │
│ last_active  │  │ created_at   │
│ failures     │  │ updated_at   │
│ created_at   │  └──────────────┘
│ updated_at   │
└──────────────┘
```

## API Endpoints

### Authentication (`/api/v1/auth`)

| Method | Path                  | Auth Required | Description                      |
|--------|-----------------------|---------------|----------------------------------|
| POST   | `/auth/register`      | No            | Register with email/password     |
| POST   | `/auth/login/email`   | No            | Login with email/password        |
| POST   | `/auth/login/firebase`| No            | Login with Firebase ID token     |
| POST   | `/auth/login/google`  | No            | Login with Google OAuth          |
| POST   | `/auth/refresh`       | No            | Refresh access token             |
| POST   | `/auth/logout`        | Yes           | Logout and revoke session(s)     |
| POST   | `/auth/password/reset`| No            | Request password reset email     |
| POST   | `/auth/password/reset/confirm` | No  | Confirm password reset           |
| POST   | `/auth/password/change`| Yes          | Change password (authenticated)  |
| POST   | `/auth/email/verify`  | No            | Verify email with token          |

### User Profile (`/api/v1/users`)

| Method | Path                    | Auth Required | Description              |
|--------|-------------------------|---------------|--------------------------|
| GET    | `/users/me`             | Yes           | Get current user profile |
| PUT    | `/users/me`             | Yes           | Update profile           |
| GET    | `/users/me/sessions`    | Yes           | List active sessions     |
| DELETE | `/users/me/sessions/:id`| Yes           | Revoke a session         |
| GET    | `/users/me/audit-log`   | Yes           | Get personal audit log   |

### Administration (`/api/v1/admin`) - Requires `admin` role

| Method | Path                         | Description               |
|--------|------------------------------|---------------------------|
| GET    | `/admin/users`               | List users with filtering |
| GET    | `/admin/users/:id`           | Get user details          |
| PUT    | `/admin/users/:id`           | Update user               |
| POST   | `/admin/users/:id/roles`     | Assign role to user       |
| DELETE | `/admin/users/:id/roles`     | Revoke role from user     |
| GET    | `/admin/users/:id/permissions`| Get user permissions     |
| GET    | `/admin/audit-logs`          | System-wide audit logs    |

## Request/Response Examples

### POST `/api/v1/auth/register`

**Request:**
```json
{
  "email": "volunteer@stadiummind.io",
  "password": "SecureP@ss123",
  "display_name": "John Volunteer"
}
```

**Response (201):**
```json
{
  "tokens": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "dGhpcyBpcyBhIHJlZnJl...",
    "token_type": "Bearer",
    "expires_in": 900
  },
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "volunteer@stadiummind.io",
    "display_name": "John Volunteer",
    "photo_url": null,
    "email_verified": false,
    "auth_provider": "email_password",
    "status": "pending_verification"
  }
}
```

### POST `/api/v1/auth/refresh`

**Request:**
```json
{
  "refresh_token": "dGhpcyBpcyBhIHJlZnJl..."
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "bmV3IHJlZnJlc2ggdG9r...",
  "token_type": "Bearer",
  "expires_in": 900
}
```

### POST `/api/v1/auth/logout`

**Request:**
```json
{
  "all_devices": false
}
```

**Response (200):**
```json
{
  "message": "Logged out successfully",
  "sessions_revoked": 1
}
```

## Authentication Flow Diagram

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Client   │     │  Firebase │     │  Backend  │     │Database  │
│(Next.js)  │     │   Auth   │     │ (FastAPI) │     │(Postgres)│
└────┬─────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘
     │                 │                 │                 │
     │  1. Login       │                 │                 │
     │  (credentials)  │                 │                 │
     │────────────────>│                 │                 │
     │                 │                 │                 │
     │  2. Firebase ID │                 │                 │
     │  Token          │                 │                 │
     │<────────────────│                 │                 │
     │                 │                 │                 │
     │  3. POST /auth/login/firebase     │                 │
     │  {id_token, fingerprint}          │                 │
     │─────────────────────────────────>│                 │
     │                 │                 │                 │
     │                 │  4. Verify      │                 │
     │                 │  Firebase Token │                 │
     │                 │<───────────────>│                 │
     │                 │                 │                 │
     │                 │                 │  5. Upsert      │
     │                 │                 │  User           │
     │                 │                 │────────────────>│
     │                 │                 │                 │
     │                 │                 │  6. Get Roles   │
     │                 │                 │────────────────>│
     │                 │                 │                 │
     │                 │                 │  7. Issue JWT   │
     │                 │                 │  + Refresh Token│
     │                 │                 │                 │
     │                 │                 │  8. Create      │
     │                 │                 │  Session        │
     │                 │                 │────────────────>│
     │                 │                 │                 │
     │  9. Auth        │                 │                 │
     │  Response       │                 │                 │
     │<─────────────────────────────────│                 │
     │                 │                 │                 │
     │  10. Store      │                 │                 │
     │  Tokens         │                 │                 │
     │  (localStorage) │                 │                 │
     │                 │                 │                 │
     │  11. API Request│                 │                 │
     │  Authorization: │                 │                 │
     │  Bearer <JWT>   │                 │                 │
     │─────────────────────────────────>│                 │
     │                 │                 │                 │
     │                 │  12. Verify JWT │                 │
     │                 │  + Check RBAC   │                 │
     │                 │                 │                 │
     │  13. Response   │                 │                 │
     │<─────────────────────────────────│                 │
```

## Sequence Diagram - Refresh Token Rotation

```
Client                    Backend                   Database
  │                         │                         │
  │  POST /auth/refresh     │                         │
  │  {refresh_token}        │                         │
  │────────────────────────>│                         │
  │                         │  Hash refresh token     │
  │                         │────────────────────────>│
  │                         │  Find session by hash   │
  │                         │<────────────────────────│
  │                         │                         │
  │                         │  Validate:              │
  │                         │  - Session exists       │
  │                         │  - Not revoked          │
  │                         │  - Not expired          │
  │                         │                         │
  │                         │  Revoke old session     │
  │                         │────────────────────────>│
  │                         │                         │
  │                         │  Issue new token pair   │
  │                         │  Create new session     │
  │                         │────────────────────────>│
  │                         │                         │
  │  {access_token,         │                         │
  │   refresh_token}        │                         │
  │<────────────────────────│                         │
```

## Threat Model

### 1. SQL Injection
- **Mitigation**: SQLAlchemy ORM with parameterized queries. Never raw SQL.

### 2. XSS (Cross-Site Scripting)
- **Mitigation**: React auto-escapes JSX. Input sanitization via `bleach` + `html.escape`. CSP headers.

### 3. CSRF (Cross-Site Request Forgery)
- **Mitigation**: SameSite cookies, Bearer token auth (no cookies for auth), CORS restrictions.

### 4. Session Fixation
- **Mitigation**: New session ID generated on every login. Old sessions invalidated.

### 5. Token Replay
- **Mitigation**: JWT expiration (15 min). Refresh token rotation. Session revocation.

### 6. JWT Theft
- **Mitigation**: Short-lived access tokens. HttpOnly cookies recommended for production. Refresh tokens stored securely.

### 7. Prompt Injection Through Profile Fields
- **Mitigation**: `sanitize_for_ai()` strips known injection patterns before any AI processing.

### 8. Broken Authentication
- **Mitigation**: Account lockout after 5 failed attempts. Rate limiting. Firebase handles password storage.

### 9. Broken Access Control
- **Mitigation**: RBAC with permission-based guards. Server-side enforcement on every endpoint.

### 10. Email Enumeration
- **Mitigation**: Password reset always returns success message regardless of email existence.

### 11. Brute Force
- **Mitigation**: Per-IP rate limiting (100 req/min). Account lockout. Progressive delays.

### 12. Token Storage on Client
- **Mitigation**: Refresh token in localStorage (acceptable for SPA). Access token in memory only.

## Security Checklist

- [x] Secrets loaded from environment variables, never hardcoded
- [x] JWT tokens have short expiration (15 min access, 7 day refresh)
- [x] Refresh token rotation on every refresh
- [x] Session invalidation on logout
- [x] Account lockout after failed attempts
- [x] Input sanitization (XSS prevention)
- [x] Prompt injection detection for AI inputs
- [x] Rate limiting middleware
- [x] Security headers (CSP, X-Frame-Options, HSTS)
- [x] CORS configuration
- [x] Stack traces never exposed to client
- [x] Soft-delete for data retention
- [x] Audit logging for all security events
- [x] UUID primary keys (non-enumerable)
- [x] Email enumeration prevention
- [x] Password complexity enforcement (8-128 chars)
- [x] Firebase handles password hashing (bcrypt)
- [x] No `any` types in TypeScript
- [x] No `console.log` in production code
- [x] Strict TypeScript compilation

## Unit Test Plan

1. `test_token_service.py`
   - Create access token and verify payload
   - Create refresh token and verify hash
   - Verify valid token succeeds
   - Verify expired token fails
   - Verify tampered token fails
   - Verify wrong issuer fails

2. `test_rbac_service.py`
   - Get user permissions returns correct set
   - has_permission returns true for assigned permission
   - has_permission returns false for unassigned permission
   - Assign role creates assignment
   - Revoke role removes assignment

3. `test_session_service.py`
   - Create session stores correctly
   - Validate session succeeds for active session
   - Validate session fails for revoked session
   - Revoke all sessions for user
   - Enforce concurrent session limit

4. `test_user_repository.py`
   - Create user persists correctly
   - Get by email finds user
   - Get by firebase UID finds user
   - Soft delete marks deleted_at
   - List with pagination works

5. `test_sanitize.py`
   - HTML stripping works
   - Email validation works
   - Prompt injection detection works
   - UUID validation works

## Integration Test Plan

1. `test_register_flow.py`
   - Register → verify user in DB → verify default role assigned → tokens returned
2. `test_login_flow.py`
   - Login → verify session created → verify audit log → tokens returned
3. `test_refresh_flow.py`
   - Refresh → old token invalidated → new tokens issued
4. `test_logout_flow.py`
   - Logout → session revoked → audit logged
5. `test_admin_flow.py`
   - Admin assigns role → user has new permissions
   - Non-admin cannot access admin endpoints

## Edge Case Test Plan

1. Register with existing email → 409 Conflict
2. Login with locked account → 423 Locked
3. Refresh with expired refresh token → 401
4. Refresh with revoked token → 401
5. Access admin endpoint without admin role → 403
6. Concurrent session limit exceeded → oldest sessions revoked
7. Account locked after MAX_LOGIN_ATTEMPTS failures
8. Account unlocked after lockout period expires
9. Password reset with non-existent email → same success response
10. Verify email with expired token

## Performance Considerations

1. **Connection Pooling**: Configured pool_size=20, max_overflow=10 for database connections
2. **Lazy Loading**: SQLAlchemy `selectinload` for relationships, `lazy="dynamic" for large collections
3. **Token Caching**: `lru_cache` on settings singleton
4. **Index Coverage**: All query patterns have matching database indexes
5. **Soft Delete Filtering**: Partial indexes with `WHERE deleted_at IS NULL`
6. **Rate Limiting**: In-memory sliding window (Redis for production)
7. **Session Cleanup**: Background job for expired session removal

## Accessibility Considerations

1. All form inputs have associated `<label>` elements
2. Error messages use `role="alert"` for screen readers
3. Status messages use `role="status"` for live regions
4. Keyboard navigation supported on all interactive elements
5. Focus states visible on all focusable elements
6. Color contrast meets WCAG AA (4.5:1 for text)
7. `aria-required` on required fields
8. Semantic HTML throughout (form, button, label, etc.)

## Deployment Notes

### Backend (Google Cloud Run)
```bash
# Build
docker build -t stadiummind-iam-backend ./backend

# Deploy
gcloud run deploy stadiummind-iam \
  --image gcr.io/stadiummind-fifa2026/iam-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "APP_ENV=production,DATABASE_URL=..." \
  --service-account stadiummind-iam@stadiummind-fifa2026.iam.gserviceaccount.com
```

### Frontend (Vercel / Cloud Run)
```bash
# Build
cd frontend && npm run build

# Deploy to Vercel
vercel --prod
```

### Database Migration
```bash
cd backend
alembic upgrade head
```

### Required Firebase Setup
1. Create Firebase project
2. Enable Authentication (Email/Password, Google)
3. Generate service account key
4. Download and place at `firebase-service-account.json`

### Required GCP IAM Roles
- `roles/cloudsql.client` (for Cloud SQL connection)
- `roles/firebase.admin` (for Firebase Admin SDK)
