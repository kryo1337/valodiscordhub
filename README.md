# ValoDiscordHub

A Discord bot + REST API platform for Valorant matchmaking, stats, and team management (think FACEIT, but for Discord).

## Features

### Queue
- Rank-based queue channels (Iron-Plat, Diamond-Ascendant, Immortal-Radiant)
- Role selection UI (Discord)
- Queue status, player count, and live updates
- Auto-timeout for inactive players

<p align="center">
  <img src="assets/queue.png" alt="Queue Channel Interface">
</p>

### Match
- Captain-based team selection (Discord)
- Side selection (Attack/Defense), auto voice channel assignment
- Score submission (with validation, Discord)
- Match results, stats, and auto-cleanup

<p align="center">
  <img src="assets/matchselection.png" alt="Match Team Selection Interface">
</p>

Score Submission:

<p align="center">
  <img src="assets/matchsubmission.png" alt="Match Score Submission Interface">
</p>

### Rank
- Riot ID verification (Discord)
- Auto rank role assignment
- Rank updates, tracking, and group categorization

<p align="center">
  <img src="assets/rank.png" alt="Rank Channel Interface">
</p>

### Leaderboard
- Global and rank-specific leaderboards (Discord)
- Points, stats, paginated display

<p align="center">
  <img src="assets/leaderboard.png" alt="Leaderboard Channel Interface">
</p>

### History
- Match history, detailed results, player stats, trends, and analysis

<p align="center">
  <img src="assets/history.png" alt="History Channel Interface">
</p>

### Stats
- Real-time player stats, role-specific metrics, win rate, KDA, historical tracking

<p align="center">
  <img src="assets/stats.png" alt="Stats Channel Interface">
</p>

### Admin
- Match management, user ban/timeout, queue control, config, dispute resolution

<p align="center">
  <img src="assets/admin.png" alt="Admin Channel Interface">
</p>

---

## Architecture

- **Discord Bot**: Python, discord.py, handles all Discord-side logic
- **REST API**: FastAPI (Python), exposes endpoints for bot and integrations
- **Database**: MongoDB (Atlas or self-hosted)
- **Containerization**: Docker for all services (bot, API, db)
- **Orchestration**: Kubernetes (Helm charts, manifests for scaling, rolling updates, secrets)
- **CI/CD**: GitHub Actions (build, test, deploy to K8s cluster)
- **Reverse Proxy**: NGINX (ingress for API)
- **Monitoring**: Prometheus + Grafana (optional, for metrics/logs)

---

## Tech Stack

- **Bot**: Python, discord.py
- **API**: FastAPI
- **DB**: MongoDB
- **Containerization**: Docker
- **Orchestration**: Kubernetes
- **CI/CD**: GitHub Actions
- **Monitoring**: Prometheus, Grafana (optional)
- **Reverse Proxy**: NGINX