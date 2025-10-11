
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
from tqdm import tqdm

# Set random seed for reproducibility
np.random.seed(42)

def simulate_game(lambda_s, lambda_r, dt=0.1, max_time=500):
    """
    Simulate a single tennis game using continuous-time Poisson process.

    Args:
        lambda_s: Server point scoring rate (points/second)
        lambda_r: Receiver point scoring rate (points/second)
        dt: Time step (seconds)
        max_time: Maximum time for the game (seconds)

    Returns:
        (winner, duration, deuce_count)
        winner: 'server' or 'receiver'
        duration: time taken (seconds)
        deuce_count: number of times game reached deuce
    """
    server_pts = 0
    receiver_pts = 0
    state = 'playing'
    deuce_count = 0
    t = 0

    while t < max_time and state != 'finished':
        t += dt

        # Check if server scores
        if np.random.rand() < lambda_s * dt:
            if state == 'playing':
                if server_pts < 3:
                    server_pts += 1
                elif server_pts == 3:
                    if receiver_pts < 3:
                        return 'server', t, deuce_count
            elif state == 'deuce':
                state = 'ad_s'
            elif state == 'ad_s':
                return 'server', t, deuce_count
            elif state == 'ad_r':
                state = 'deuce'

        # Check if receiver scores
        elif np.random.rand() < lambda_r * dt:
            if state == 'playing':
                if receiver_pts < 3:
                    receiver_pts += 1
                elif receiver_pts == 3:
                    if server_pts < 3:
                        return 'receiver', t, deuce_count
            elif state == 'deuce':
                state = 'ad_r'
            elif state == 'ad_r':
                return 'receiver', t, deuce_count
            elif state == 'ad_s':
                state = 'deuce'

        # Check if we just reached deuce
        if state == 'playing' and server_pts == 3 and receiver_pts == 3:
            state = 'deuce'
            deuce_count += 1

    # If we hit max time, whoever is ahead wins
    # This shouldn't happen often and may need to be changed
    return 'server' if server_pts > receiver_pts else 'receiver', t, deuce_count


def simulate_tiebreak(lambda_s, lambda_r, dt=0.1, max_time=500):
    """
    Simulate a tiebreak using continuous-time Poisson process.
    Players alternate serves every 2 points.

    Returns:
        (winner, duration, final_score)
        winner: 'player1' or 'player2'
        duration: time taken (seconds)
        final_score: (p1_points, p2_points)
    """
    p1_pts = 0
    p2_pts = 0
    t = 0
    total_points = 0

    while t < max_time:
        t += dt

        # Determine who is serving (alternates every 2 points)
        # Player 1 serves points 0, 3, 4, 7, 8, ...
        # Player 2 serves points 1, 2, 5, 6, 9, ...
        serve_pattern = total_points % 4
        is_p1_serving = serve_pattern in [0, 3]

        # Determine scoring rates based on who is serving
        if is_p1_serving:
            rate_p1 = lambda_s
            rate_p2 = lambda_r
        else:
            rate_p1 = lambda_r
            rate_p2 = lambda_s

        # Check if player 1 scores
        if np.random.rand() < rate_p1 * dt:
            p1_pts += 1
            total_points += 1
            # Check win condition
            if p1_pts >= 7 and p1_pts - p2_pts >= 2:
                return 'player1', t, (p1_pts, p2_pts)

        # Check if player 2 scores
        elif np.random.rand() < rate_p2 * dt:
            p2_pts += 1
            total_points += 1
            # Check win condition
            if p2_pts >= 7 and p2_pts - p1_pts >= 2:
                return 'player2', t, (p1_pts, p2_pts)

    # Timeout - whoever is ahead wins
    return ('player1' if p1_pts > p2_pts else 'player2'), t, (p1_pts, p2_pts)


def simulate_set(lambda_s, lambda_r, dt=0.1):
    """
    Simulate a tennis set (first to 6 games with 2-game lead, tiebreak at 6-6).

    Returns:
        (winner, games_p1, games_p2, duration, stats)
        winner: 'player1' or 'player2'
        games_p1, games_p2: games won by each player
        duration: total time (seconds)
        stats: dict with detailed statistics
    """
    games_p1 = 0
    games_p2 = 0
    total_time = 0
    deuce_count = 0
    games_played = 0

    while True:
        games_played += 1

        # Determine who is serving (alternates)
        if games_played % 2 == 1:
            # Player 1 serves
            winner, duration, deuces = simulate_game(lambda_s, lambda_r, dt)
            if winner == 'server':
                games_p1 += 1
            else:
                games_p2 += 1
        else:
            # Player 2 serves
            winner, duration, deuces = simulate_game(lambda_s, lambda_r, dt)
            if winner == 'server':
                games_p2 += 1
            else:
                games_p1 += 1

        total_time += duration
        deuce_count += deuces

        # Check for set win (standard rules)
        if games_p1 >= 6 or games_p2 >= 6:
            if abs(games_p1 - games_p2) >= 2:
                winner = 'player1' if games_p1 > games_p2 else 'player2'
                stats = {
                    'deuce_count': deuce_count,
                    'games_played': games_played,
                    'tiebreak_played': False
                }
                return winner, games_p1, games_p2, total_time, stats

        # Check for tiebreak
        if games_p1 == 6 and games_p2 == 6:
            winner, duration, tb_score = simulate_tiebreak(lambda_s, lambda_r, dt)
            total_time += duration
            if winner == 'player1':
                games_p1 = 7
            else:
                games_p2 = 7
            winner = 'player1' if games_p1 > games_p2 else 'player2'
            stats = {
                'deuce_count': deuce_count,
                'games_played': games_played + 1,  # +1 for tiebreak
                'tiebreak_played': True,
                'tiebreak_score': tb_score
            }
            return winner, games_p1, games_p2, total_time, stats


def simulate_match(lambda_s, lambda_r, best_of=3, dt=0.1):
    """
    Simulate a full tennis match (best of 3 or best of 5 sets).

    Returns:
        (winner, set_scores, duration, stats)
        winner: 'player1' or 'player2'
        set_scores: list of (p1_games, p2_games) tuples
        duration: total match time (seconds)
        stats: dict with detailed statistics
    """
    sets_p1 = 0
    sets_p2 = 0
    set_scores = []
    total_time = 0
    sets_needed = (best_of // 2) + 1

    total_games = 0
    total_deuces = 0
    tiebreaks_played = 0

    while sets_p1 < sets_needed and sets_p2 < sets_needed:
        winner, games_p1, games_p2, duration, stats = simulate_set(lambda_s, lambda_r, dt)

        if winner == 'player1':
            sets_p1 += 1
        else:
            sets_p2 += 1

        set_scores.append((games_p1, games_p2))
        total_time += duration
        total_games += stats['games_played']
        total_deuces += stats['deuce_count']
        if stats['tiebreak_played']:
            tiebreaks_played += 1

    match_stats = {
        'total_games': total_games,
        'total_deuces': total_deuces,
        'tiebreaks_played': tiebreaks_played,
        'sets_played': len(set_scores)
    }

    winner = 'player1' if sets_p1 > sets_p2 else 'player2'
    return winner, set_scores, total_time, match_stats


# ==============================================================
# ============= SIMULATION PARAMETERS ==========================
# ==============================================================
np.random.seed(42)

lambda_s = 0.95 / 30  # server scoring rate (points/sec)
lambda_r = 0.05 / 30  # receiver scoring rate
n_matches = 5000
best_of = 3
dt = 0.1

# ==============================================================
# ============= RUN SIMULATIONS ================================
# ==============================================================
results = []
for _ in tqdm(range(n_matches)):
    winner, set_scores, duration, stats = simulate_match(lambda_s, lambda_r, best_of, dt)
    results.append({
        "winner": winner,
        "sets_played": stats["sets_played"],
        "total_games": stats["total_games"],
        "total_deuces": stats["total_deuces"],
        "tiebreaks": stats["tiebreaks_played"],
        "duration": duration,
        "set_scores": set_scores
    })

# ==============================================================
# ============= SUMMARY STATISTICS =============================
# ==============================================================
winners = [r["winner"] for r in results]
durations = [r["duration"] for r in results]
games = [r["total_games"] for r in results]
deuces = [r["total_deuces"] for r in results]
sets_played = [r["sets_played"] for r in results]
tiebreaks = [r["tiebreaks"] for r in results]

p1_win_rate = winners.count("player1") / n_matches * 100
p2_win_rate = 100 - p1_win_rate

print("="*60)
print(f"Matches simulated: {n_matches:,}")
print(f"Server scoring rate λ_s = {lambda_s:.4f}, Receiver λ_r = {lambda_r:.4f}")
print("-"*60)
print(f"Average match duration: {np.mean(durations):.1f} s")
print(f"Average games per match: {np.mean(games):.2f}")
print(f"Average deuces per match: {np.mean(deuces):.2f}")
print(f"Tiebreaks per match: {np.mean(tiebreaks):.3f}")
print(f"Sets per match: {np.mean(sets_played):.2f}")
print("="*60)

# ==============================================================
# ============= VISUALIZATION ==================================
# ==============================================================
fig, axes = plt.subplots(2, 2, figsize=(12, 10))
fig.suptitle("Simulated Tennis Match Statistics", fontsize=14, fontweight='bold')

# 1. Match duration histogram
axes[0, 0].hist(durations, bins=30, edgecolor='black', alpha=0.7)
axes[0, 0].set_title("Distribution of Match Durations (sec)")
axes[0, 0].set_xlabel("Duration (seconds)")
axes[0, 0].set_ylabel("Frequency")

# 2. Games per match
axes[0, 1].hist(games, bins=range(min(games), max(games)+1), alpha=0.7, edgecolor='black')
axes[0, 1].set_title("Distribution of Games per Match")
axes[0, 1].set_xlabel("Games per Match")
axes[0, 1].set_ylabel("Count")

# 3. Pie chart of match winners
axes[1, 0].pie(
    [p1_win_rate, p2_win_rate],
    labels=["Player 1", "Player 2"],
    autopct='%1.1f%%',
    colors=["skyblue", "salmon"],
    startangle=90
)
axes[1, 0].set_title("Match Win Rates")

# 4. Scatter: total deuces vs match duration
axes[1, 1].scatter(deuces, durations, alpha=0.4, edgecolors='k')
axes[1, 1].set_xlabel("Total Deuces per Match")
axes[1, 1].set_ylabel("Match Duration (s)")
axes[1, 1].set_title("Deuce Frequency vs Match Length")
axes[1, 1].grid(True, alpha=0.3)

plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.savefig("match_simulation.png", bbox_inches="tight")
plt.show()