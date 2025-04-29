# ValoDiscordHub

A Discord bot that provides a comprehensive Valorant matchmaking and statistics system, similar to FACEIT.

## Features

### Queue
- Rank-based queue channels (Iron-Plat, Diamond-Ascendant, Immortal-Radiant)
- Role selection interface with buttons for each role
- Queue status and player count display
- Auto-timeout system for inactive players

<p align="center">
  <img src="assets/queue.png" alt="Queue Channel Interface">
</p>

### Match
- Team selection interface with captain-based picking
- Side selection (Attack/Defense) with voice channel assignments
- Score submission with validation
- Match results and statistics display
- Auto-cleanup of match channels after completion

Team Selection:

<p align="center">
  <img src="assets/matchselection.png" alt="Match Team Selection Interface">
</p>

Score Submission:

<p align="center">
  <img src="assets/matchsubmission.png" alt="Match Score Submission Interface">
</p>

### Rank
- Rank verification interface with Riot ID input
- Automatic rank role assignment
- Rank updates and tracking system
- Rank group categorization

<p align="center">
  <img src="assets/rank.png" alt="Rank Channel Interface">
</p>

### Leaderboard
- Global leaderboard with points system
- Rank-specific leaderboards
- Performance statistics and rankings
- Paginated leaderboard display

<p align="center">
  <img src="assets/leaderboard.png" alt="Leaderboard Channel Interface">
</p>

### History
- Match history with detailed results
- Player statistics and performance tracking
- Performance trends and analysis
- Historical match data

<p align="center">
  <img src="assets/history.png" alt="History Channel Interface">
</p>

### Stats
- Real-time player statistics
- Performance metrics display
- Role-specific statistics
- Historical performance tracking
- Win rate and KDA analytics

<p align="center">
  <img src="assets/stats.png" alt="Stats Channel Interface">
</p>

### Admin
- Match management interface
- User ban/timeout system
- Queue control and monitoring
- System configuration settings
- Match dispute resolution

<p align="center">
  <img src="assets/admin.png" alt="Admin Channel Interface">
</p>

## Technical Stack
- Python-based Discord bot
- MongoDB database
- Docker containerization
- Discord.py framework
