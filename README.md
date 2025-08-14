# ValoDiscordHub

End-to-end Discord platform for Valorant in-guild matchmaking: queues, captain draft, side selection, score validation, leaderboard, history, stats, and admin tooling. Bot-first UX with a typed FastAPI backend and MongoDB.

## What the client gets

- Matchmaking inside Discord with guardrails and automation
- Clear player journeys: Verify rank → Queue → Draft → Play → Submit score → Leaderboard/History updates
- Admin controls for disputes, bans, timeouts, rank/points adjustments
- Docker/Kubernetes deployment, rate-limited API, secrets-managed config

## How it works (flow)

1) Rank verification (once per user)
- User opens `#rank` and requests verification; a ticket goes to `#admin-ranks`
- Admin selects the rank; bot assigns the rank-group role: `iron-plat`, `dia-asc`, `imm-radiant`

2) Queueing by rank group
- Users click “Queue” in `#queue-<group>`; bot enforces cooldowns, bans/timeouts
- When 10 players gather, bot auto-creates a match lobby (text + voice)

3) Captain draft
- Two captains are chosen (top points or random fallback)
- Captains pick players via UI with timeout and progress indicators

4) Side selection
- Opposing captain picks Attack/Defense (with timeout fallback)

5) Score submission and validation
- Captains submit scores; mismatches trigger an admin alert in `#admin`
- On valid result, bot updates leaderboard, stats, and history, then cleans up channels

## Feature overview (shipped)

### Queue
- Rank-grouped channels with live player list and progress bar
- Join/leave button, cooldowns, and auto-match on 10 players

<p align="center">
  <img src="assets/queue.png" alt="Queue Channel Interface">
</p>

### Match
- Captain draft UI, automatic team voice channels, side selection
- Score submission with discrepancy handling and admin escalation

<p align="center">
  <img src="assets/matchselection.png" alt="Match Team Selection Interface">
</p>

Score Submission:

<p align="center">
  <img src="assets/matchsubmission.png" alt="Match Score Submission Interface">
</p>

### Rank
- Ticketed rank verification (with tracker.gg link helper)
- Assigns rank-group roles for access control

<p align="center">
  <img src="assets/rank.png" alt="Rank Channel Interface">
</p>

### Leaderboard
- Rank-group leaderboards with per-user paginated views and preferences

<p align="center">
  <img src="assets/leaderboard.png" alt="Leaderboard Channel Interface">
</p>

### History
- Match cards with captains, sides, score, duration, and timestamp

<p align="center">
  <img src="assets/history.png" alt="History Channel Interface">
</p>

### Stats
- My stats / search player; rank group context, win/loss breakdown, streaks

<p align="center">
  <img src="assets/stats.png" alt="Stats Channel Interface">
</p>

### Admin
- Set result/cancel, ban/timeout/unban, set rank/points, refresh channels, list bans/timeouts, rank tickets

<p align="center">
  <img src="assets/admin.png" alt="Admin Channel Interface">
</p>

## Architecture

- Discord Bot (discord.py) with cogs: `queue`, `match`, `rank`, `leaderboard`, `history`, `stats`, `admin`
- FastAPI backend exposing REST for the bot; MongoDB for persistence
- Containerized via Docker; optional Kubernetes manifests in `k8s/`
- API rate limiting (IP-based; bot traffic bypass via Bot token)

## Data model (API layer)

- `Player`: `discord_id`, `riot_id`, `rank`, counters (wins/losses), computed `winrate`
- `Match`: `match_id`, teams, captains, `lobby_master`, `rank_group`, `defense_start`, scores, `result`, timestamps, computed `duration`
- `Leaderboard`: `rank_group`, array of player entries with `points`, `matches_played`, `winrate`, `streak`
- `Queue`: `rank_group`, `players` list with `joined_at`
- `UserPreferences`: per-user `rank_group`, pagination settings

## API surface (selected)

- Players: `GET/POST/PATCH /players` and `/players/{discord_id}`
- Matches: `GET /matches/active`, `POST /matches`, `GET/PATCH /matches/{match_id}`
- Leaderboard: `GET /leaderboard`, `GET/PUT /leaderboard/{rank_group}`
- Queue: `GET /queue/{rank_group}`, `POST /{rank_group}/join|leave`, `PUT /{rank_group}`, `DELETE /{rank_group}`
- History: recent/all/player matches under `/history`
- Stats: `GET /stats/{discord_id}` with optional `rank_group`
- Admin logs and checks under `/admin` (ban/timeout listings, status checks)

Auth/Security:
- Bot → API: `Authorization: Bot <BOT_API_TOKEN>` (required on mutating routes)
- Web auth ready: `/auth/login` → Discord OAuth → `/auth/callback` issues JWT (HS256)

## Reliability & safeguards

- API rate limit: 60 req/min per IP; bot traffic bypassed via `Bot` token
- Bot-side cooldowns per command (`queue`, `rank`, `stats`) and robust error handling
- Score discrepancy detection routes to `#admin` with actionable embeds
- Automatic cleanup of match channels on completion/cancel

## Roadmap / nice-to-haves

- Web dashboard (read-only first: leaderboards, stats, history)
- Persistent cooldown store (Redis) and distributed rate limiting
- MMR/elo curve tuning, map vetoes
- Observability (metrics, structured logs), SLOs

---

## Tech Stack

- Bot: Python, discord.py
- API: FastAPI, httpx
- DB: MongoDB (motor)
- Auth: Discord OAuth2 + JWT (HS256)
- Infra: Docker, optional Kubernetes
- Extras: Playwright (rank scraping helper)
