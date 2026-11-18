# Sign in with kevsrobots

How an app outside `.kevsrobots.com` (Snakie on app.snakie.org, the Snakie desktop app, or a future suite app) signs
someone in with their kevsrobots account and gets a token for them. Issue #80.

Apps on `*.kevsrobots.com` (kevsrobots.com, BetterCAD) don't need this: they keep using the shared `access_token`
cookie.

It is standard OAuth 2 authorization code flow with PKCE (RFC 6749, RFC 7636), with loopback redirects for desktop
apps (RFC 8252). There is no client secret: apps are public clients, and PKCE stops a stolen code being used.

## 1. Register the app

Clients are added by Kev, not self-service. Add an entry to `DEFAULT_CLIENTS` in `app/oauth.py` (it is created on
startup if missing), or insert a row into `oauth_clients`:

| Field           | Example                                                           |
|-----------------|-------------------------------------------------------------------|
| `client_id`     | `snakie`                                                          |
| `name`          | `Snakie` (shown on the consent page and in Connected apps)        |
| `redirect_uris` | `https://app.snakie.org/auth/callback http://127.0.0.1/callback` |
| `scopes`        | `profile projects:read projects:write`                            |

Redirect URIs must match exactly. The one exception is a loopback entry (`http://127.0.0.1/…` or `http://[::1]/…`),
which allows that path on any port, so a desktop app can listen on whatever port is free.

To show the "Continue to …" chip on the sign-in page, add the client to `CLIENT_APPS` in `app/suite.py`.

## 2. Scopes

| Scope            | Lets the app                                          |
|------------------|-------------------------------------------------------|
| `profile`        | See your name and profile picture (`/oauth/userinfo`) |
| `projects:read`  | See your kevsrobots projects, so you can pick one     |
| `projects:write` | Add wiring diagrams and parts lists to your projects  |

No scope touches code: code stays on GitHub. Ask only for what the action needs.

## 3. Send the person to sign in

Make a random `code_verifier` (43 to 128 characters of `A-Z a-z 0-9 - . _ ~`) and a random `state`, keep both, then
open:

```
https://accounts.kevsrobots.com/oauth/authorize
  ?response_type=code
  &client_id=snakie
  &redirect_uri=https://app.snakie.org/auth/callback
  &scope=profile projects:write
  &state=<state>
  &code_challenge=<BASE64URL(SHA256(code_verifier)), no padding>
  &code_challenge_method=S256
```

(`chatter.kevsrobots.com` works too and forwards to accounts.kevsrobots.com.)

- Desktop: listen on `http://127.0.0.1:<free port>/callback` and open the URL in the system browser, not an
  embedded web view.
- If the person isn't signed in, they see the kevsrobots sign-in page first.
- The first time, they see one consent screen: "Allow Snakie to use your account?" with the scopes in plain words.
  Next time, if they already allowed those scopes, they go straight back.

The browser comes back to `redirect_uri?code=…&state=…`. Check `state` matches. On failure it comes back with
`error` (`access_denied` if they pressed Cancel, `invalid_scope`, `invalid_request`, `unsupported_response_type`)
and `error_description`. An unknown client or a redirect URI that isn't registered shows an error page instead of
redirecting.

## 4. Swap the code for tokens

The code works once and lasts 60 seconds.

```
POST /oauth/token
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code&client_id=snakie&code=<code>&code_verifier=<verifier>
&redirect_uri=https://app.snakie.org/auth/callback
```

```json
{
  "access_token": "eyJ…",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "…",
  "scope": "profile projects:write"
}
```

Errors are `400` with `{"error": "invalid_grant", "error_description": "…"}` (or `invalid_request`,
`unsupported_grant_type`, and `401 invalid_client`). Using a code twice also disconnects whatever the first use
signed in.

CORS allows `https://app.snakie.org`. Desktop apps call from the main process, so CORS doesn't apply.

## 5. Call APIs

Send `Authorization: Bearer <access_token>`. The access token is a Chatter JWT with `sub` (username), `client_id`,
`scope` and `gid` (the grant) claims, valid for 1 hour.

App tokens only work on routes that check a scope with `require_scope("…")` from `app/oauth.py`. Every other
Chatter route (account, password, likes, comments) answers `403 App tokens can't be used here`, so an app can never
change someone's account. A missing scope answers `403` with
`WWW-Authenticate: Bearer error="insufficient_scope", scope="…"`. A disconnected app answers `401`.

`GET /oauth/userinfo` (scope `profile`) returns `username`, `name`, `picture` and `profile_url`.

Services that verify Chatter JWTs themselves (the projects API in kevsrobots.com `stacks/projects-api`) should
check the `scope` claim whenever `client_id` is present, and treat tokens without `client_id` as full sign-ins.

## 6. Stay signed in

When the access token expires, refresh it:

```
POST /oauth/token
grant_type=refresh_token&client_id=snakie&refresh_token=<refresh_token>
```

You get a new access token and a new refresh token. Each refresh token works once and lasts 90 days. If an old
refresh token is used again, the app is disconnected (someone may have copied it), and the person has to sign in
again. Desktop apps should keep the refresh token in the OS keychain.

## 7. Sign out

```
POST /oauth/revoke
token=<refresh or access token>&client_id=snakie
```

Always answers `200`. People can also disconnect an app themselves under **Connected apps** on `/account`.

## Storage

Tables `oauth_clients`, `oauth_codes`, `oauth_grants` and `oauth_refresh_tokens` (migration 020). Codes and refresh
tokens are stored as SHA-256 hashes only.
