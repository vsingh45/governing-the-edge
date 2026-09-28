# Say It Better: personal Deep-dive backend

A tiny FastAPI server that answers the iOS app's Deep dive and "Try it yourself" requests with
Claude, via the **Claude Agent SDK**. It uses your own Claude Code login, so usage comes out of your
Claude subscription instead of separately billed API calls.

It's meant for your own devices. Don't distribute it or ship it through the App Store.

## Setup (on your Mac)

1. Install Claude Code and log in once (`claude` → `/login`). For a server that runs without a
   terminal attached, create a long-lived token:
   ```bash
   claude setup-token
   export CLAUDE_CODE_OAUTH_TOKEN=...   # the token it prints
   ```
2. Install and run:
   ```bash
   cd backend
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn server:app --host 0.0.0.0 --port 8765
   ```
3. Check it from the Mac:
   ```bash
   curl http://localhost:8765/health
   curl "http://localhost:8765/deepdive?word=cadence"
   curl -X POST http://localhost:8765/checkSentence \
        -H 'Content-Type: application/json' \
        -d '{"word":"cadence","sentence":"We should agree a cadence for release reviews."}'
   ```

Optional: set `SAYITBETTER_MODEL` to choose a specific model. Otherwise the Claude Code default is used.

## Point the app at it

In the app, tap the gear icon, go to **Deep dive backend**, and enter:

- **Same Wi-Fi:** `http://<your-mac-name>.local:8765`. Find the name in System Settings → General →
  Sharing → Local hostname. iOS asks for Local Network permission the first time.
- **Anywhere:** install [Tailscale](https://tailscale.com) on the Mac and the iPhone, then use
  `http://<mac>.<tailnet>.ts.net:8765` or the Mac's `100.x.y.z` Tailscale IP. You don't need port
  forwarding.

Tap **Test** to confirm. If the backend can't be reached, Deep dive quietly falls back to the
content bundled in the app. Sentence feedback needs the backend.

## Notes

- Each call runs Claude with **no tools** (`tools=[]`) and ignores local settings files, so all it
  can do is write text.
- Deep dives are cached in memory per word until you restart the server.
- There's no auth. Only bind it to networks you trust (home Wi-Fi, your tailnet).
