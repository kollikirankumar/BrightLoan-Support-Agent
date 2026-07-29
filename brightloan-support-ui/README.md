# brightloan-support-ui

React frontend for the Brightloan AI Support Agent. Implements the UI spec in
[`../02-frontend-react-auth.md`](../02-frontend-react-auth.md) — Google
sign-in, chat window, grounded-answer citations, and human-handoff cards.

## Setup

```bash
npm install
cp .env.example .env
npm run dev
```

That's it — no Google OAuth credentials needed to run it right now. With
`VITE_GOOGLE_CLIENT_ID` left blank in `.env`, the sign-in screen falls back to
a local dev sign-in (just type a name). See `src/components/SignInScreen.jsx`
and `src/context/AuthContext.jsx` (`loginAsGuest`) for how that works.

### Enabling real Google sign-in (later)

1. [Google Cloud Console](https://console.cloud.google.com/) → **APIs &
   Services → Credentials → Create Credentials → OAuth client ID** → Web
   application.
2. Add `http://localhost:5173` under Authorized JavaScript origins.
3. Put the client ID in `.env` as `VITE_GOOGLE_CLIENT_ID=...` and restart
   `npm run dev`. `SignInScreen` automatically switches to the real
   `GoogleLogin` button once this is set — no code changes needed.

## Backend dependency

This app expects a backend implementing the API contract described in
`02-frontend-react-auth.md` §6 (`POST /auth/google`, `POST /chat`,
`GET /chat/history`, `POST /auth/logout`) at `http://localhost:8000`, proxied
via `vite.config.js` during dev. Until that backend exists (see
`01-architecture.md` through `07-data-model-extensibility.md`), the chat UI
will accept your name/message but sending a message will fail — expected at
this stage of the build. Google sign-in specifically (once enabled) would hit
the same wall: it succeeds against Google, but the follow-up
`POST /auth/google` call to the backend has nothing to answer it yet.

## Structure

```
src/
  api/client.js          fetch wrapper matching the backend API contract
  context/AuthContext.jsx auth state — loginWithGoogle (real) + loginAsGuest (dev fallback), logout
  hooks/useChat.js         chat message state + send/receive logic
  components/
    SignInScreen.jsx
    ChatLayout.jsx
    Header.jsx
    MessageList.jsx
    UserMessage.jsx
    AgentMessage.jsx       grounded answers + source citation pills
    HandoffCard.jsx        human handoff assignment card
    TypingIndicator.jsx    staged loading text
    ChatInput.jsx
```

## Notes

- `useChat.js` currently does one request/response round trip per turn. The
  backend contract allows for streaming (SSE) later — swap `api.sendMessage`
  for a stream reader there when the backend supports it; no other component
  needs to change.
- Sign-in is required before chatting (no guest mode) — matches the v1 scope
  in the PRD.
