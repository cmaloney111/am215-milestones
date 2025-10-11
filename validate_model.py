import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
import re
from collections import Counter

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
    state = "playing"
    deuce_count = 0
    t = 0

    while t < max_time and state != "finished":
        t += dt

        # Check if server scores
        if np.random.rand() < lambda_s * dt:
            if state == "playing":
                if server_pts < 3:
                    server_pts += 1
                elif server_pts == 3:
                    if receiver_pts < 3:
                        return "server", t, deuce_count
            elif state == "deuce":
                state = "ad_s"
            elif state == "ad_s":
                return "server", t, deuce_count
            elif state == "ad_r":
                state = "deuce"

        # Check if receiver scores
        elif np.random.rand() < lambda_r * dt:
            if state == "playing":
                if receiver_pts < 3:
                    receiver_pts += 1
                elif receiver_pts == 3:
                    if server_pts < 3:
                        return "receiver", t, deuce_count
            elif state == "deuce":
                state = "ad_r"
            elif state == "ad_r":
                return "receiver", t, deuce_count
            elif state == "ad_s":
                state = "deuce"

        # Check if we just reached deuce
        if state == "playing" and server_pts == 3 and receiver_pts == 3:
            state = "deuce"
            deuce_count += 1

    # If we hit max time, whoever is ahead wins
    # This shouldn't happen often and may need to be changed
    return "server" if server_pts > receiver_pts else "receiver", t, deuce_count


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
                return "player1", t, (p1_pts, p2_pts)

        # Check if player 2 scores
        elif np.random.rand() < rate_p2 * dt:
            p2_pts += 1
            total_points += 1
            # Check win condition
            if p2_pts >= 7 and p2_pts - p1_pts >= 2:
                return "player2", t, (p1_pts, p2_pts)

    # Timeout - whoever is ahead wins
    return ("player1" if p1_pts > p2_pts else "player2"), t, (p1_pts, p2_pts)


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
            if winner == "server":
                games_p1 += 1
            else:
                games_p2 += 1
        else:
            # Player 2 serves
            winner, duration, deuces = simulate_game(lambda_r, lambda_s, dt)
            if winner == "server":
                games_p2 += 1
            else:
                games_p1 += 1

        total_time += duration
        deuce_count += deuces

        # Check for set win (standard rules)
        if games_p1 >= 6 or games_p2 >= 6:
            if abs(games_p1 - games_p2) >= 2:
                winner = "player1" if games_p1 > games_p2 else "player2"
                stats = {
                    "deuce_count": deuce_count,
                    "games_played": games_played,
                    "tiebreak_played": False,
                }
                return winner, games_p1, games_p2, total_time, stats

        # Check for tiebreak
        if games_p1 == 6 and games_p2 == 6:
            winner, duration, tb_score = simulate_tiebreak(lambda_s, lambda_r, dt)
            total_time += duration
            if winner == "player1":
                games_p1 = 7
            else:
                games_p2 = 7
            winner = "player1" if games_p1 > games_p2 else "player2"
            stats = {
                "deuce_count": deuce_count,
                "games_played": games_played + 1,  # +1 for tiebreak
                "tiebreak_played": True,
                "tiebreak_score": tb_score,
            }
            return winner, games_p1, games_p2, total_time, stats


def simulate_match(lambda_s, lambda_r, best_of=3, dt=0.1):
    lambda_s = 0.0025
    lambda_r = 0.0025
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
        winner, games_p1, games_p2, duration, stats = simulate_set(
            lambda_s, lambda_r, dt
        )

        if winner == "player1":
            sets_p1 += 1
        else:
            sets_p2 += 1

        set_scores.append((games_p1, games_p2))
        total_time += duration
        total_games += stats["games_played"]
        total_deuces += stats["deuce_count"]
        if stats["tiebreak_played"]:
            tiebreaks_played += 1

    match_stats = {
        "total_games": total_games,
        "total_deuces": total_deuces,
        "tiebreaks_played": tiebreaks_played,
        "sets_played": len(set_scores),
    }

    winner = "player1" if sets_p1 > sets_p2 else "player2"
    return winner, set_scores, total_time, match_stats


# ============= DATA LOADING AND PARSING =============


def parse_score(score_str):
    """
    Parse ATP score string into set scores.

    Examples:
        "6-4 7-6(5)" -> [(6, 4), (7, 6)]
        "6-3 4-6 7-5" -> [(6, 3), (4, 6), (7, 5)]

    Returns:
        List of (winner_games, loser_games) tuples, or None if parsing fails
    """
    if pd.isna(score_str) or score_str == "":
        return None

    # Remove tiebreak scores in parentheses for simplicity
    score_str = re.sub(r"\([^)]*\)", "", score_str)

    # Split by spaces to get individual sets
    sets = score_str.strip().split()

    set_scores = []
    for set_score in sets:
        if "-" in set_score:
            try:
                parts = set_score.split("-")
                winner_games = int(parts[0])
                loser_games = int(parts[1])
                set_scores.append((winner_games, loser_games))
            except (ValueError, IndexError):
                continue

    return set_scores if len(set_scores) > 0 else None


def load_atp_data(filename="atp_matches_2024.csv"):
    """Load and parse ATP match data."""
    df = pd.read_csv(filename)

    # Filter to matches with valid data
    df = df[df["score"].notna()].copy()
    df = df[df["minutes"].notna()].copy()
    df = df[df["best_of"] == 3].copy()  # Focus on best of 3 for now

    # Parse scores
    df["parsed_score"] = df["score"].apply(parse_score)
    df = df[df["parsed_score"].notna()].copy()

    # Calculate number of sets
    df["num_sets"] = df["parsed_score"].apply(len)

    # Calculate total games
    df["total_games"] = df["parsed_score"].apply(
        lambda scores: sum(g1 + g2 for g1, g2 in scores)
    )

    # Check if any set went to tiebreak (7-6)
    df["had_tiebreak"] = df["parsed_score"].apply(
        lambda scores: any(
            (g1 == 7 and g2 == 6) or (g1 == 6 and g2 == 7) for g1, g2 in scores
        )
    )

    print(f"Loaded {len(df)} valid ATP matches from 2024")
    print(f"  - Mean duration: {df['minutes'].mean():.1f} minutes")
    print(f"  - Mean total games: {df['total_games'].mean():.1f}")
    print(
        f"  - Matches with tiebreaks: {df['had_tiebreak'].sum()} ({df['had_tiebreak'].mean() * 100:.1f}%)"
    )
    print(
        f"  - Match length distribution: {df['num_sets'].value_counts().sort_index().to_dict()}"
    )

    return df


# ============= MODEL VALIDATION =============


def run_simulation_batch(lambda_s, lambda_r, n_matches=1000, best_of=3):
    """
    Run a batch of match simulations and collect statistics.
    """
    results = {
        "durations": [],
        "total_games": [],
        "num_sets": [],
        "had_tiebreak": [],
        "set_scores": [],
    }

    for _ in range(n_matches):
        winner, set_scores, duration, stats = simulate_match(
            lambda_s, lambda_r, best_of
        )

        results["durations"].append(duration / 60)  # Convert to minutes
        results["total_games"].append(stats["total_games"])
        results["num_sets"].append(stats["sets_played"])
        results["had_tiebreak"].append(stats["tiebreaks_played"] > 0)
        results["set_scores"].append(set_scores)

    return results


def compare_distributions(real_data, sim_results):
    """
    Compare real and simulated data distributions.
    """
    print("\n" + "=" * 70)
    print("DISTRIBUTION COMPARISON")
    print("=" * 70)

    # Duration comparison
    real_durations = real_data["minutes"].values
    sim_durations = np.array(sim_results["durations"])

    print(f"\nMatch Duration (minutes):")
    print(
        f"  Real: mean={np.mean(real_durations):.1f}, std={np.std(real_durations):.1f}, median={np.median(real_durations):.1f}"
    )
    print(
        f"  Sim:  mean={np.mean(sim_durations):.1f}, std={np.std(sim_durations):.1f}, median={np.median(sim_durations):.1f}"
    )

    # KS test for duration
    ks_stat, ks_pval = stats.ks_2samp(real_durations, sim_durations)
    print(f"  KS test: statistic={ks_stat:.4f}, p-value={ks_pval:.4f}")

    # Total games comparison
    real_games = real_data["total_games"].values
    sim_games = np.array(sim_results["total_games"])

    print(f"\nTotal Games per Match:")
    print(f"  Real: mean={np.mean(real_games):.1f}, std={np.std(real_games):.1f}")
    print(f"  Sim:  mean={np.mean(sim_games):.1f}, std={np.std(sim_games):.1f}")

    # Number of sets comparison
    real_sets_dist = real_data["num_sets"].value_counts(normalize=True).sort_index()
    sim_sets_dist = (
        pd.Series(sim_results["num_sets"]).value_counts(normalize=True).sort_index()
    )

    print(f"\nNumber of Sets Distribution:")
    print(f"  Real: {real_sets_dist.to_dict()}")
    print(f"  Sim:  {sim_sets_dist.to_dict()}")

    # Tiebreak frequency
    real_tb_freq = real_data["had_tiebreak"].mean()
    sim_tb_freq = np.mean(sim_results["had_tiebreak"])

    print(f"\nTiebreak Frequency:")
    print(f"  Real: {real_tb_freq * 100:.1f}%")
    print(f"  Sim:  {sim_tb_freq * 100:.1f}%")

    print("=" * 70 + "\n")

    return {
        "duration_ks": (ks_stat, ks_pval),
        "duration_diff": abs(np.mean(real_durations) - np.mean(sim_durations)),
        "games_diff": abs(np.mean(real_games) - np.mean(sim_games)),
        "tiebreak_diff": abs(real_tb_freq - sim_tb_freq),
    }


def plot_comparisons(real_data, sim_results, lambda_s, lambda_r):
    """
    Create visualization comparing real and simulated data.
    """
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))

    # Plot 1: Duration distribution
    ax = axes[0, 0]
    ax.hist(
        real_data["minutes"],
        bins=30,
        alpha=0.5,
        label="Real Data",
        density=True,
        color="blue",
    )
    ax.hist(
        sim_results["durations"],
        bins=30,
        alpha=0.5,
        label="Simulation",
        density=True,
        color="red",
    )
    ax.set_xlabel("Match Duration (minutes)")
    ax.set_ylabel("Density")
    ax.set_title("Match Duration Distribution")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Plot 2: Total games distribution
    ax = axes[0, 1]
    ax.hist(
        real_data["total_games"],
        bins=range(10, 50),
        alpha=0.5,
        label="Real Data",
        density=True,
        color="blue",
    )
    ax.hist(
        sim_results["total_games"],
        bins=range(10, 50),
        alpha=0.5,
        label="Simulation",
        density=True,
        color="red",
    )
    ax.set_xlabel("Total Games per Match")
    ax.set_ylabel("Density")
    ax.set_title("Total Games Distribution")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Plot 3: Number of sets (handle mismatched categories)
    ax = axes[0, 2]
    real_sets = real_data["num_sets"].value_counts(normalize=True).sort_index()
    sim_sets = (
        pd.Series(sim_results["num_sets"]).value_counts(normalize=True).sort_index()
    )

    # Get union of all categories and reindex with zero-fill
    all_categories = sorted(set(real_sets.index) | set(sim_sets.index))
    real_sets_aligned = real_sets.reindex(all_categories, fill_value=0)
    sim_sets_aligned = sim_sets.reindex(all_categories, fill_value=0)

    x = np.arange(len(all_categories))
    width = 0.35
    ax.bar(
        x - width / 2,
        real_sets_aligned.values,
        width,
        label="Real Data",
        color="blue",
        alpha=0.7,
    )
    ax.bar(
        x + width / 2,
        sim_sets_aligned.values,
        width,
        label="Simulation",
        color="red",
        alpha=0.7,
    )
    ax.set_xlabel("Number of Sets")
    ax.set_ylabel("Frequency")
    ax.set_title("Match Length Distribution")
    ax.set_xticks(x)
    ax.set_xticklabels(all_categories)
    ax.legend()
    ax.grid(True, alpha=0.3, axis="y")

    # Plot 4: Q-Q plot for duration
    ax = axes[1, 0]
    stats.probplot(real_data["minutes"], dist="norm", plot=ax)
    ax.set_title("Q-Q Plot: Real Duration")
    ax.grid(True, alpha=0.3)

    # Plot 5: Set score heatmap (winner perspective)
    ax = axes[1, 1]
    # Count set score frequencies
    real_set_counts = Counter()
    for scores in real_data["parsed_score"]:
        for score in scores:
            real_set_counts[score] += 1

    sim_set_counts = Counter()
    for scores in sim_results["set_scores"]:
        for score in scores:
            sim_set_counts[score] += 1

    # Create comparison
    all_scores = sorted(set(real_set_counts.keys()) | set(sim_set_counts.keys()))
    real_freqs = [real_set_counts.get(s, 0) / len(real_data) for s in all_scores]
    sim_freqs = [
        sim_set_counts.get(s, 0) / len(sim_results["durations"]) for s in all_scores
    ]

    x_pos = np.arange(len(all_scores))
    width = 0.35
    ax.bar(
        x_pos - width / 2, real_freqs, width, label="Real Data", color="blue", alpha=0.7
    )
    ax.bar(
        x_pos + width / 2, sim_freqs, width, label="Simulation", color="red", alpha=0.7
    )
    ax.set_xlabel("Set Score (Winner-Loser)")
    ax.set_ylabel("Frequency per Match")
    ax.set_title("Set Score Distribution")
    ax.set_xticks(x_pos)
    ax.set_xticklabels([f"{s[0]}-{s[1]}" for s in all_scores], rotation=45)
    ax.legend()
    ax.grid(True, alpha=0.3, axis="y")

    # Plot 6: Tiebreak frequency
    ax = axes[1, 2]
    categories = ["No Tiebreak", "Has Tiebreak"]
    real_tb = [1 - real_data["had_tiebreak"].mean(), real_data["had_tiebreak"].mean()]
    sim_tb = [
        1 - np.mean(sim_results["had_tiebreak"]),
        np.mean(sim_results["had_tiebreak"]),
    ]
    x_pos = np.arange(len(categories))
    width = 0.35
    ax.bar(
        x_pos - width / 2, real_tb, width, label="Real Data", color="blue", alpha=0.7
    )
    ax.bar(x_pos + width / 2, sim_tb, width, label="Simulation", color="red", alpha=0.7)
    ax.set_ylabel("Frequency")
    ax.set_title("Tiebreak Occurrence")
    ax.set_xticks(x_pos)
    ax.set_xticklabels(categories)
    ax.legend()
    ax.grid(True, alpha=0.3, axis="y")

    plt.suptitle(
        f"Model Validation: λ_s={lambda_s:.5f}, λ_r={lambda_r:.5f}",
        fontsize=14,
        fontweight="bold",
    )
    plt.tight_layout()
    plt.savefig("model_validation.png", dpi=150, bbox_inches="tight")
    print("\nVisualization saved to 'model_validation.png'")
    return fig


# ============= PARAMETER OPTIMIZATION =============


def estimate_parameters_from_data(real_data):
    """
    Estimate lambda_s and lambda_r from real match data.

    Strategy: Use matches where we have service point statistics.
    """
    # Filter to matches with service statistics
    stat_matches = real_data[
        (real_data["w_svpt"].notna())
        & (real_data["l_svpt"].notna())
        & (real_data["minutes"].notna())
    ].copy()

    print(f"\nMatches with service statistics: {len(stat_matches)}")

    if len(stat_matches) > 0:
        # Calculate points per second
        stat_matches["total_points"] = stat_matches["w_svpt"] + stat_matches["l_svpt"]
        stat_matches["points_per_sec"] = stat_matches["total_points"] / (
            stat_matches["minutes"] * 60
        )

        # Estimate from winner/loser split
        # Assume winner wins ~55-65% of points on average
        mean_points_per_sec = stat_matches["points_per_sec"].mean()

        # Calculate service point win percentages
        stat_matches["w_srv_win_pct"] = (
            stat_matches["w_1stWon"] + stat_matches["w_2ndWon"]
        ) / stat_matches["w_svpt"]

        stat_matches["l_srv_win_pct"] = (
            stat_matches["l_1stWon"] + stat_matches["l_2ndWon"]
        ) / stat_matches["l_svpt"]

        mean_server_win_rate = pd.concat(
            [stat_matches["w_srv_win_pct"], stat_matches["l_srv_win_pct"]]
        ).mean()

        print(f"\nEstimated statistics from data:")
        print(f"  Mean points per second: {mean_points_per_sec:.5f}")
        print(f"  Mean server win rate: {mean_server_win_rate:.3f}")

        # Estimate lambda_s and lambda_r
        # If server wins p% of points, then lambda_s / (lambda_s + lambda_r) = p
        lambda_total = mean_points_per_sec
        lambda_s = lambda_total * mean_server_win_rate
        lambda_r = lambda_total * (1 - mean_server_win_rate)

        print(f"\nEstimated parameters:")
        print(f"  λ_s = {lambda_s:.5f} points/sec")
        print(f"  λ_r = {lambda_r:.5f} points/sec")
        print(f"  Server advantage: {lambda_s / (lambda_s + lambda_r) * 100:.1f}%")

        return lambda_s, lambda_r
    else:
        # Fallback to testing.py parameters
        print("\nNo service statistics available, using testing.py parameters")
        return 0.65 / 30, 0.35 / 30


def grid_search_parameters(real_data, n_sims=500):
    """
    Try different parameter values and find the best fit.
    """
    print("\n" + "=" * 70)
    print("GRID SEARCH FOR OPTIMAL PARAMETERS")
    print("=" * 70)

    # Define parameter grid
    server_advantages = [0.5]  # Server win probability
    total_rates = [0.5]  # Total points per second

    best_params = None
    best_score = float("inf")
    results_table = []

    for srv_adv in server_advantages:
        for total_rate in total_rates:
            lambda_s = total_rate * srv_adv
            lambda_r = total_rate * (1 - srv_adv)

            print(f"\nTesting λ_s={lambda_s:.5f}, λ_r={lambda_r:.5f}...", end=" ")

            # Run simulations
            sim_results = run_simulation_batch(lambda_s, lambda_r, n_matches=n_sims)

            # Calculate fit score (weighted combination of errors)
            duration_error = abs(
                np.mean(real_data["minutes"]) - np.mean(sim_results["durations"])
            )
            games_error = abs(
                np.mean(real_data["total_games"]) - np.mean(sim_results["total_games"])
            )
            tb_error = (
                abs(
                    real_data["had_tiebreak"].mean()
                    - np.mean(sim_results["had_tiebreak"])
                )
                * 100
            )

            # Weighted score (you can adjust these weights)
            score = duration_error * 0.5 + games_error * 2.0 + tb_error * 0.5

            print(
                f"Score={score:.2f} (dur_err={duration_error:.1f}, game_err={games_error:.1f}, tb_err={tb_error:.2f})"
            )

            results_table.append(
                {
                    "lambda_s": lambda_s,
                    "lambda_r": lambda_r,
                    "srv_adv": srv_adv,
                    "score": score,
                    "duration_error": duration_error,
                    "games_error": games_error,
                    "tb_error": tb_error,
                }
            )

            if score < best_score:
                best_score = score
                best_params = (lambda_s, lambda_r)
                best_results = sim_results

    print("\n" + "=" * 70)
    print(f"BEST PARAMETERS: λ_s={best_params[0]:.5f}, λ_r={best_params[1]:.5f}")
    print(f"Best score: {best_score:.2f}")
    print("=" * 70)

    # Show top 5 parameter combinations
    results_df = pd.DataFrame(results_table).sort_values("score")
    print("\nTop 5 parameter combinations:")
    print(results_df.head().to_string(index=False))

    return best_params, best_results


# ============= MAIN EXECUTION =============

if __name__ == "__main__":
    print("=" * 70)
    print("TENNIS MODEL VALIDATION")
    print("Extending continuous-time Poisson process to sets and matches")
    print("=" * 70)

    # Load real data
    print("\n[1/5] Loading ATP match data...")
    real_data = load_atp_data("atp_matches_2024.csv")

    # Estimate parameters from data
    print("\n[2/5] Estimating parameters from data...")
    lambda_s_estimated, lambda_r_estimated = estimate_parameters_from_data(real_data)

    # Run initial validation with estimated parameters
    print(f"\n[3/5] Running validation with estimated parameters...")
    print(f"  Simulating {1000} matches (this may take a minute)...")
    sim_results_estimated = run_simulation_batch(
        lambda_s_estimated, lambda_r_estimated, n_matches=1000
    )

    # Compare distributions
    print("\n[4/5] Comparing distributions...")
    metrics_estimated = compare_distributions(real_data, sim_results_estimated)

    # Run grid search for optimal parameters
    print("\n[5/5] Running grid search for optimal parameters...")
    best_params, best_sim_results = grid_search_parameters(real_data, n_sims=500)

    # Final comparison with best parameters
    print("\n" + "=" * 70)
    print("FINAL VALIDATION WITH OPTIMIZED PARAMETERS")
    print("=" * 70)

    # Run more simulations with best parameters
    print(f"\nRunning 2000 matches with optimized parameters...")
    final_sim_results = run_simulation_batch(
        best_params[0], best_params[1], n_matches=2000
    )

    final_metrics = compare_distributions(real_data, final_sim_results)

    # Generate visualizations
    print("\nGenerating comparison plots...")
    plot_comparisons(real_data, final_sim_results, best_params[0], best_params[1])

    print("\n" + "=" * 70)
    print("VALIDATION COMPLETE!")
    print("=" * 70)
    print(f"\nOptimal parameters found:")
    print(f"  λ_s = {best_params[0]:.5f} points/sec")
    print(f"  λ_r = {best_params[1]:.5f} points/sec")
    print(
        f"  Server advantage: {best_params[0] / (best_params[0] + best_params[1]) * 100:.1f}%"
    )
    print(f"\nKey metrics:")
    print(f"  Duration error: {final_metrics['duration_diff']:.2f} minutes")
    print(f"  Games error: {final_metrics['games_diff']:.2f} games")
    print(f"  Tiebreak frequency error: {final_metrics['tiebreak_diff'] * 100:.2f}%")
    print(f"  KS test p-value: {final_metrics['duration_ks'][1]:.4f}")

    print("\nOutputs saved:")
    print("  - model_validation.png")
    print("\n" + "=" * 70)
