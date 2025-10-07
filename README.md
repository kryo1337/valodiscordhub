# ValoDiscordHub

End-to-end Discord platform for Valorant in-guild matchmaking: queues, captain draft, side selection, score validation, leaderboard, history, stats, and admin tooling. Bot-first UX with a typed FastAPI backend and MongoDB.

## How it works

1. Rank verification (once per user)

- User opens `#rank` and requests verification; a ticket goes to `#admin-ranks`
- Admin selects the rank; bot assigns the rank-group role: `iron-plat`, `dia-asc`, `imm-radiant`

2. Queueing by rank group

- Users click “Queue” in `#queue-<group>`; bot enforces cooldowns, bans/timeouts
- When 10 players gather, bot auto-creates a match lobby (text + voice)

3. Captain draft

- Two captains are chosen (top points or random fallback)
- Captains pick players via UI with timeout and progress indicators

4. Maps selection

- Captains ban maps for current rotation

5. Side selection

- Opposing captain picks Attack/Defense (with timeout fallback)

6. Score submission and validation

- Captains submit scores; mismatches trigger an admin alert in `#admin`
- On valid result, bot updates leaderboard, stats, and history, then cleans up channels

## Feature overview

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

---

## Architecture

- Discord Bot (discord.py) with cogs: `queue`, `match`, `rank`, `leaderboard`, `history`, `stats`, `admin`
- FastAPI backend exposing REST for the bot; MongoDB for persistence
- Containerized via Docker; optional Kubernetes manifests in `k8s/`
- API rate limiting (IP-based; bot traffic bypass via Bot token)

## Tech Stack

- Bot: Python, discord.py
- API: FastAPI, httpx
- DB: MongoDB (motor)
- Auth: Discord OAuth2 + JWT (HS256)
- Infra: Docker, optional Kubernetes
