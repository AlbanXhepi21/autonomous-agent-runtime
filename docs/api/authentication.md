# API: Authentication

Full lifecycle and security model in
[authentication-and-tenancy.md](../architecture/authentication-and-tenancy.md) — this page
is the request/response reference for `/api/v1/auth/*`.

## Register

```http
POST /api/v1/auth/register
Content-Type: application/json

{"email": "person@example.com", "password": "at-least-8-chars", "display_name": "Person Name"}
```

`201` → `UserResponse`:

```json
{
  "id": "…", "email": "person@example.com", "display_name": "Person Name",
  "is_active": true, "email_verified": false,
  "created_at": "…", "updated_at": "…", "last_login_at": null
}
```

**Registering does not log you in** — no cookies are set by this call. `409` if the email
is already registered; `422` for a weak password (below 8 characters).

## Log in

```http
POST /api/v1/auth/login
Content-Type: application/json

{"email": "person@example.com", "password": "at-least-8-chars"}
```

`200` → the same `UserResponse` shape, and — only here — two cookies are set:

| Cookie | `HttpOnly` | `SameSite` | Purpose |
|---|---|---|---|
| `session_token` | Yes | Lax | The session identifier; never readable from JavaScript |
| `csrf_token` | No | Lax | Copy this value into an `X-CSRF-Token` header on every mutating request |

`401` for a wrong password, `403` if the account has been disabled. A nonexistent email
takes the same time to reject as a wrong password (a fixed dummy password hash is checked
either way) — this API cannot be used to enumerate registered accounts by timing.

## Log out

```http
POST /api/v1/auth/logout          # this session only
POST /api/v1/auth/logout-all      # every session for this user
```

Both require `X-CSRF-Token`. `200` → `{"message": "..."}`.

## Who am I

```http
GET /api/v1/auth/me
```

`200` → `UserResponse` for the caller's own session; `401` if the session cookie is
missing, expired (idle or absolute TTL — see
[authentication-and-tenancy.md](../architecture/authentication-and-tenancy.md#session-and-token-behavior)),
or revoked.

## Change password (authenticated)

```http
POST /api/v1/auth/change-password
X-CSRF-Token: <csrf_token cookie value>

{"current_password": "...", "new_password": "..."}
```

Revokes every other session for the account except the one making this request.

## Forgot / reset password

```http
POST /api/v1/auth/forgot-password
{"email": "person@example.com"}
```

Responds identically whether or not the email is registered — no observable difference in
the response, by design, so this endpoint can't be used to enumerate accounts either.

```http
POST /api/v1/auth/reset-password
{"token": "...", "new_password": "..."}
```

Redeems a one-time token (mailed by `forgot-password`) and revokes **every** session for
that user. `400 {"code": "invalid_token", ...}` for an invalid or expired token.

## Email verification

```http
POST /api/v1/auth/verify-email/resend   # requires X-CSRF-Token
POST /api/v1/auth/verify-email/confirm
{"token": "..."}
```

## CSRF, precisely

`require_csrf` compares `hash_token(X-CSRF-Token header)` against the **session's own**
stored `csrf_token_hash` — not merely "does the header match the cookie." A request
missing the header, or carrying a header that doesn't hash to what this specific session
was issued, is rejected regardless of what cookie value is present. See
[authentication-and-tenancy.md](../architecture/authentication-and-tenancy.md#csrf-behavior)
for the one route currently missing this protection.

## What does not exist

No OAuth/social login, no SSO/SAML, no multi-factor authentication, no passwordless/
magic-link login. See [limitations.md](../reference/limitations.md#authentication-features-not-yet-implemented).
