# Say It Better (iOS)

A native SwiftUI rebuild of the Say It Better vocabulary app: 40 words that help an engineer sound
like a lead in meetings, grouped as **Process, Problems, Decisions, Speaking**.

- **Learn**: one card at a time with everything visible at once: word, pronunciation, definition,
  six "goes with" phrases, the example sentence with the word highlighted, and the "instead of
  saying…" swap. Tap the speaker to hear the word. **Still learning** puts the card back about three
  cards later; **I know this** marks it known.
- **Quiz**: 10 questions per round, alternating *fill the blank* and *say it better*, with
  same-part-of-speech distractors, a score at the end, and a history of recent rounds.
- **My words**: every known word A–Z with its phrases and example shown in the row, plus
  **Relearn**.
- **All words**: search (word, meaning, or the "instead of" phrase) with a known/learning toggle on
  each row.
- **Deep dive** (from any card or row): meaning, origin, word family, collocations, near-synonyms,
  a common mistake, examples by meeting setting, a memory tip, reference links, and a
  "write your own sentence" feedback box.

## Run it

Requirements: Xcode 16+, iOS 17+ simulator or device.

1. Open `SayItBetter.xcodeproj`. The project uses Xcode 16 folder-synced groups, so any file you add
   under `SayItBetter/` is picked up automatically.
2. Pick an iPhone simulator and press **Run**.
3. **Signing.** On a device, set your team under *Signing & Capabilities* and change the bundle ID
   from `com.example.SayItBetter` to one of your own. iCloud Key-Value sync needs a paid developer
   team. With a free Personal Team, delete the `CODE_SIGN_ENTITLEMENTS` build setting (or the iCloud
   capability). The app then keeps progress on the device only, with no code changes.

## How it's put together

```
SayItBetter/
  App/            SayItBetterApp (SwiftData container, environment), RootView (tab bar)
  Models/         Word (+ loader, example-sentence parsing), DeepDive, QuizResult (@Model)
  Store/          WordStore (@Observable: words, known set, shared category filter)
                  KnownWordsSync (UserDefaults + iCloud Key-Value Store)
  Services/       DeepDiveService (live backend → bundled fallback), QuizBuilder, Speaker, ReferenceLinks
  Views/          LearnView, QuizView, MyWordsView, AllWordsView, DeepDiveSheet, SettingsView, Components/
  Resources/      words.json (the 40 words), deepdive.json (pre-generated deep dives)
backend/          Optional personal server: Claude Agent SDK + FastAPI
```

- **Content is data.** To add words, append entries to `Resources/words.json` using the same shape.
  Wrap the target word in the `example` in `[brackets]`. Add a matching entry to `deepdive.json`, or
  let the backend generate it live.
- **Known words** live in `UserDefaults` for instant reads and are mirrored to
  `NSUbiquitousKeyValueStore`, so they follow your iCloud account across devices. If iCloud isn't
  available, sync turns off silently.
- **Quiz history** is stored with SwiftData.
- **Deep dive** first shows the bundled content right away. If a backend URL is set in Settings
  (gear icon) and the backend answers, the live version from Claude replaces it. Sentence feedback
  needs the backend. Offline, the app only checks that you used the word.

## Live Deep dive with your Claude subscription (optional)

iOS apps can't sign in with a Claude Pro/Max subscription directly. Instead, `backend/` runs a small
server on your Mac that uses the **Claude Agent SDK** with your own Claude Code login. See
[`backend/README.md`](backend/README.md) for setup, then enter `http://<your-mac>.local:8765` (or
your Tailscale address) in the app's Settings. This setup is for your own devices only, not for
App Store distribution.
