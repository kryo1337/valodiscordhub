# ValoDiscordHub

A Discord bot that provides a comprehensive Valorant matchmaking and statistics system, similar to FACEIT.

## Features

### Queue
- Rank-based queue channels (Iron-Plat, Diamond-Ascendant, Immortal-Radiant)
- Role selection interface with buttons for each role
- Queue status and player count display
- Auto-timeout system for inactive players
![Queue Channel Interface](assets/screenshots/queue.png)

### Match
- Team selection interface with captain-based picking
- Side selection (Attack/Defense) with voice channel assignments
- Score submission with validation
- Match results and statistics display
- Auto-cleanup of match channels after completion

Team Selection:
![Match Team Selection Interface](assets/screenshots/matchselection.png)

Score Submission:
![Match Score Submission Interface](assets/screenshots/matchsubmission.png)

### Rank
- Rank verification interface with Riot ID input
- Automatic rank role assignment
- Rank updates and tracking system
- Rank group categorization
![Rank Channel Interface](assets/screenshots/rank.png)

### Leaderboard
- Global leaderboard with points system
- Rank-specific leaderboards
- Performance statistics and rankings
- Paginated leaderboard display
![Leaderboard Channel Interface](assets/screenshots/leaderboard.png)

### History
- Match history with detailed results
- Player statistics and performance tracking
- Performance trends and analysis
- Historical match data
![History Channel Interface](assets/screenshots/history.png)

### Stats
- Real-time player statistics
- Performance metrics display
- Role-specific statistics
- Historical performance tracking
- Win rate and KDA analytics
![Stats Channel Interface](assets/screenshots/stats.png)

### Admin
- Match management interface
- User ban/timeout system
- Queue control and monitoring
- System configuration settings
- Match dispute resolution
![Admin Channel Interface](assets/screenshots/admin.png)

## Technical Stack
- Python-based Discord bot
- MongoDB database
- Docker containerization
- Discord.py framework
