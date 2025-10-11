import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from scipy.spatial.distance import jensenshannon
import re
from collections import Counter
from pathlib import Path
import warnings
from tqdm import tqdm
warnings.filterwarnings('ignore')

# Set random seed for reproducibility
np.random.seed(42)

# ============= SIMULATION FUNCTIONS (from validate_model.py) =============

def simulate_game(lambda_s, lambda_r, dt=0.1, max_time=500):
    """
    Simulate a single tennis game using continuous-time Poisson process.
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

    return 'server' if server_pts > receiver_pts else 'receiver', t, deuce_count


def simulate_tiebreak(lambda_s, lambda_r, dt=0.1, max_time=500):
    """
    Simulate a tiebreak using continuous-time Poisson process.
    """
    p1_pts = 0
    p2_pts = 0
    t = 0
    total_points = 0

    while t < max_time:
        t += dt

        serve_pattern = total_points % 4
        is_p1_serving = serve_pattern in [0, 3]

        if is_p1_serving:
            rate_p1 = lambda_s
            rate_p2 = lambda_r
        else:
            rate_p1 = lambda_r
            rate_p2 = lambda_s

        if np.random.rand() < rate_p1 * dt:
            p1_pts += 1
            total_points += 1
            if p1_pts >= 7 and p1_pts - p2_pts >= 2:
                return 'player1', t, (p1_pts, p2_pts)

        elif np.random.rand() < rate_p2 * dt:
            p2_pts += 1
            total_points += 1
            if p2_pts >= 7 and p2_pts - p1_pts >= 2:
                return 'player2', t, (p1_pts, p2_pts)

    return ('player1' if p1_pts > p2_pts else 'player2'), t, (p1_pts, p2_pts)


def simulate_set(lambda_s, lambda_r, dt=0.1):
    """
    Simulate a tennis set (first to 6 games with 2-game lead, tiebreak at 6-6).
    """
    games_p1 = 0
    games_p2 = 0
    total_time = 0
    deuce_count = 0
    games_played = 0

    while True:
        games_played += 1

        if games_played % 2 == 1:
            winner, duration, deuces = simulate_game(lambda_s, lambda_r, dt)
            if winner == 'server':
                games_p1 += 1
            else:
                games_p2 += 1
        else:
            winner, duration, deuces = simulate_game(lambda_r, lambda_s, dt)
            if winner == 'server':
                games_p2 += 1
            else:
                games_p1 += 1

        total_time += duration
        deuce_count += deuces

        if games_p1 >= 6 or games_p2 >= 6:
            if abs(games_p1 - games_p2) >= 2:
                winner = 'player1' if games_p1 > games_p2 else 'player2'
                stats = {
                    'deuce_count': deuce_count,
                    'games_played': games_played,
                    'tiebreak_played': False
                }
                return winner, games_p1, games_p2, total_time, stats

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
                'games_played': games_played + 1,
                'tiebreak_played': True,
                'tiebreak_score': tb_score
            }
            return winner, games_p1, games_p2, total_time, stats


def simulate_match(lambda_s, lambda_r, best_of=3, dt=0.1):
    """
    Simulate a full tennis match (best of 3 or best of 5 sets).
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


def run_simulation_batch(lambda_s, lambda_r, n_matches=1000, best_of=3):
    """
    Run a batch of match simulations and collect statistics.
    """
    results = {
        'durations': [],
        'total_games': [],
        'num_sets': [],
        'had_tiebreak': [],
        'set_scores': []
    }

    for _ in tqdm(range(n_matches)):
        winner, set_scores, duration, stats = simulate_match(lambda_s, lambda_r, best_of)

        results['durations'].append(duration / 60)  # Convert to minutes
        results['total_games'].append(stats['total_games'])
        results['num_sets'].append(stats['sets_played'])
        results['had_tiebreak'].append(stats['tiebreaks_played'] > 0)
        results['set_scores'].append(set_scores)

    return results


# ============= DATA LOADING AND PARSING =============

def parse_score(score_str):
    """
    Parse ATP score string into set scores.
    """
    if pd.isna(score_str) or score_str == '':
        return None

    score_str = re.sub(r'\([^)]*\)', '', score_str)
    sets = score_str.strip().split()

    set_scores = []
    for set_score in sets:
        if '-' in set_score:
            try:
                parts = set_score.split('-')
                winner_games = int(parts[0])
                loser_games = int(parts[1])
                set_scores.append((winner_games, loser_games))
            except (ValueError, IndexError):
                continue

    return set_scores if len(set_scores) > 0 else None


def load_all_atp_data(data_dir='tennis_atp', years_range=None, best_of=3):
    """
    Load ATP match data from all years in the directory.
    """
    data_path = Path(data_dir)
    all_files = sorted(data_path.glob('atp_matches_[0-9]*.csv'))

    dfs = []
    for file in all_files:
        try:
            year = int(file.stem.split('_')[-1])
            if years_range and (year < years_range[0] or year > years_range[1]):
                continue

            df = pd.read_csv(file)
            df['year'] = year
            dfs.append(df)
        except Exception as e:
            print(f"Warning: Could not load {file}: {e}")
            continue

    if not dfs:
        raise ValueError("No data files found")

    combined_df = pd.concat(dfs, ignore_index=True)

    # Filter and clean
    combined_df = combined_df[combined_df['score'].notna()].copy()
    combined_df = combined_df[combined_df['minutes'].notna()].copy()
    combined_df = combined_df[combined_df['best_of'] == best_of].copy()

    # Parse scores
    combined_df['parsed_score'] = combined_df['score'].apply(parse_score)
    combined_df = combined_df[combined_df['parsed_score'].notna()].copy()

    # Calculate metrics
    combined_df['num_sets'] = combined_df['parsed_score'].apply(len)
    combined_df['total_games'] = combined_df['parsed_score'].apply(
        lambda scores: sum(g1 + g2 for g1, g2 in scores)
    )
    combined_df['had_tiebreak'] = combined_df['parsed_score'].apply(
        lambda scores: any((g1 == 7 and g2 == 6) or (g1 == 6 and g2 == 7)
                          for g1, g2 in scores)
    )

    print(f"\nLoaded {len(combined_df)} valid ATP matches")
    if years_range:
        print(f"  Years: {years_range[0]}-{years_range[1]}")
    else:
        print(f"  Years: {combined_df['year'].min()}-{combined_df['year'].max()}")
    print(f"  Mean duration: {combined_df['minutes'].mean():.1f} minutes")
    print(f"  Mean total games: {combined_df['total_games'].mean():.1f}")
    print(f"  Tiebreak frequency: {combined_df['had_tiebreak'].mean()*100:.1f}%")

    return combined_df


# ============= PARAMETER OPTIMIZATION =============

def estimate_parameters_from_data(data, verbose=True):
    """
    Estimate lambda_s and lambda_r from real match data.
    """
    stat_matches = data[
        (data['w_svpt'].notna()) &
        (data['l_svpt'].notna()) &
        (data['minutes'].notna())
    ].copy()

    if verbose:
        print(f"  Matches with service statistics: {len(stat_matches)}")

    if len(stat_matches) > 0:
        stat_matches['total_points'] = stat_matches['w_svpt'] + stat_matches['l_svpt']
        stat_matches['points_per_sec'] = stat_matches['total_points'] / (stat_matches['minutes'] * 60)

        mean_points_per_sec = stat_matches['points_per_sec'].mean()

        stat_matches['w_srv_win_pct'] = (
            stat_matches['w_1stWon'] + stat_matches['w_2ndWon']
        ) / stat_matches['w_svpt']

        stat_matches['l_srv_win_pct'] = (
            stat_matches['l_1stWon'] + stat_matches['l_2ndWon']
        ) / stat_matches['l_svpt']

        mean_server_win_rate = pd.concat([
            stat_matches['w_srv_win_pct'],
            stat_matches['l_srv_win_pct']
        ]).mean()

        lambda_total = mean_points_per_sec
        lambda_s = lambda_total * mean_server_win_rate
        lambda_r = lambda_total * (1 - mean_server_win_rate)

        if verbose:
            print(f"  Mean points per second: {mean_points_per_sec:.5f}")
            print(f"  Mean server win rate: {mean_server_win_rate:.3f}")
            print(f"  Initial λ_s = {lambda_s:.5f}, λ_r = {lambda_r:.5f}")

        return lambda_s, lambda_r
    else:
        if verbose:
            print("  No service statistics available, using default parameters")
        return 0.65 / 30, 0.35 / 30


def optimize_parameters(train_data, n_sims=200, verbose=True):
    """
    Optimize parameters using grid search (similar to validate_model.py).
    """
    if verbose:
        print("  Optimizing parameters via grid search...")

    # Get initial estimates
    lambda_s_init, lambda_r_init = estimate_parameters_from_data(train_data, verbose=False)

    # Define parameter grid around initial estimates (reduced for speed)
    server_advantages = [0.60, 0.63, 0.65, 0.67, 0.70]  # Server win probability
    total_rates = [0.023, 0.025, 0.027, 0.030]  # Total points per second

    best_params = None
    best_score = float('inf')

    for srv_adv in server_advantages:
        for total_rate in total_rates:
            lambda_s = total_rate * srv_adv
            lambda_r = total_rate * (1 - srv_adv)

            # Run simulations
            sim_results = run_simulation_batch(lambda_s, lambda_r, n_matches=n_sims)

            # Calculate fit score (weighted combination of errors)
            duration_error = abs(np.mean(train_data['minutes']) - np.mean(sim_results['durations']))
            games_error = abs(np.mean(train_data['total_games']) - np.mean(sim_results['total_games']))
            tb_error = abs(train_data['had_tiebreak'].mean() - np.mean(sim_results['had_tiebreak'])) * 100

            # Weighted score
            score = duration_error * 0.5 + games_error * 2.0 + tb_error * 0.5

            if score < best_score:
                best_score = score
                best_params = (lambda_s, lambda_r)

    if verbose:
        print(f"  Optimized λ_s = {best_params[0]:.5f}, λ_r = {best_params[1]:.5f}")
        print(f"  Optimization score: {best_score:.2f}")

    return best_params


# ============= BASELINE MODELS =============

def baseline_50_50(n_matches=1000, best_of=3):
    """
    Baseline: 50-50 server/receiver model (no server advantage).
    """
    # Use equal rates that produce reasonable match length
    lambda_s = lambda_r = 0.0165  # Equal rates
    return run_simulation_batch(lambda_s, lambda_r, n_matches, best_of)


# ============= STATISTICAL METRICS =============

def wasserstein_distance(real, sim):
    """Calculate Wasserstein distance between two distributions."""
    return stats.wasserstein_distance(real, sim)


def kl_divergence(real, sim, bins=30):
    """
    Calculate KL divergence between two continuous distributions.
    """
    min_val = min(real.min(), sim.min())
    max_val = max(real.max(), sim.max())
    bins_edges = np.linspace(min_val, max_val, bins + 1)

    real_hist, _ = np.histogram(real, bins=bins_edges, density=True)
    sim_hist, _ = np.histogram(sim, bins=bins_edges, density=True)

    real_hist = real_hist / real_hist.sum()
    sim_hist = sim_hist / sim_hist.sum()

    eps = 1e-10
    real_hist = real_hist + eps
    sim_hist = sim_hist + eps

    real_hist = real_hist / real_hist.sum()
    sim_hist = sim_hist / sim_hist.sum()

    return np.sum(real_hist * np.log(real_hist / sim_hist))


def js_divergence(real, sim, bins=30):
    """
    Calculate Jensen-Shannon divergence (symmetric version of KL).
    """
    min_val = min(real.min(), sim.min())
    max_val = max(real.max(), sim.max())
    bins_edges = np.linspace(min_val, max_val, bins + 1)

    real_hist, _ = np.histogram(real, bins=bins_edges, density=True)
    sim_hist, _ = np.histogram(sim, bins=bins_edges, density=True)

    real_hist = real_hist / real_hist.sum()
    sim_hist = sim_hist / sim_hist.sum()

    return jensenshannon(real_hist, sim_hist) ** 2


def chi_square_test(real_counts, sim_counts):
    """
    Chi-square test for categorical distributions.
    """
    all_categories = sorted(set(real_counts.keys()) | set(sim_counts.keys()))

    observed = np.array([sim_counts.get(cat, 0) for cat in all_categories])
    expected = np.array([real_counts.get(cat, 0) for cat in all_categories])

    if expected.sum() > 0:
        expected = expected * (observed.sum() / expected.sum())

    chi2, p_value = stats.chisquare(observed, expected)

    return chi2, p_value


def proportion_test(real_prop, sim_prop, n_real, n_sim):
    """
    Two-proportion z-test.
    """
    p_pooled = (real_prop * n_real + sim_prop * n_sim) / (n_real + n_sim)
    se = np.sqrt(p_pooled * (1 - p_pooled) * (1/n_real + 1/n_sim))

    if se == 0:
        return 0, 1.0

    z = (real_prop - sim_prop) / se
    p_value = 2 * (1 - stats.norm.cdf(abs(z)))

    return z, p_value


def compute_all_metrics(real_data, sim_results, model_name="Model"):
    """
    Compute all comparison metrics between real and simulated data.
    """
    metrics = {'model': model_name}

    # Duration metrics
    real_dur = real_data['minutes'].values
    sim_dur = np.array(sim_results['durations'])

    metrics['duration_mean_real'] = np.mean(real_dur)
    metrics['duration_mean_sim'] = np.mean(sim_dur)
    metrics['duration_mean_diff'] = abs(np.mean(real_dur) - np.mean(sim_dur))
    metrics['duration_wasserstein'] = wasserstein_distance(real_dur, sim_dur)
    metrics['duration_kl_div'] = kl_divergence(real_dur, sim_dur)
    metrics['duration_js_div'] = js_divergence(real_dur, sim_dur)

    ks_stat, ks_pval = stats.ks_2samp(real_dur, sim_dur)
    metrics['duration_ks_stat'] = ks_stat
    metrics['duration_ks_pval'] = ks_pval

    # Total games metrics
    real_games = real_data['total_games'].values
    sim_games = np.array(sim_results['total_games'])

    metrics['games_mean_real'] = np.mean(real_games)
    metrics['games_mean_sim'] = np.mean(sim_games)
    metrics['games_mean_diff'] = abs(np.mean(real_games) - np.mean(sim_games))
    metrics['games_wasserstein'] = wasserstein_distance(real_games, sim_games)
    metrics['games_kl_div'] = kl_divergence(real_games, sim_games, bins=20)
    metrics['games_js_div'] = js_divergence(real_games, sim_games, bins=20)

    # Number of sets (categorical)
    real_sets_counts = real_data['num_sets'].value_counts().to_dict()
    sim_sets_counts = pd.Series(sim_results['num_sets']).value_counts().to_dict()

    chi2, chi2_pval = chi_square_test(real_sets_counts, sim_sets_counts)
    metrics['sets_chi2'] = chi2
    metrics['sets_chi2_pval'] = chi2_pval

    # Tiebreak proportion
    real_tb_prop = real_data['had_tiebreak'].mean()
    sim_tb_prop = np.mean(sim_results['had_tiebreak'])

    z_stat, z_pval = proportion_test(
        real_tb_prop, sim_tb_prop,
        len(real_data), len(sim_results['durations'])
    )

    metrics['tiebreak_prop_real'] = real_tb_prop
    metrics['tiebreak_prop_sim'] = sim_tb_prop
    metrics['tiebreak_prop_diff'] = abs(real_tb_prop - sim_tb_prop)
    metrics['tiebreak_z_stat'] = z_stat
    metrics['tiebreak_z_pval'] = z_pval

    return metrics


# ============= CROSS-VALIDATION =============

def k_fold_cross_validation(data, k=5, n_sims=1000, n_optimize=300):
    """
    Perform k-fold cross-validation.
    """
    print(f"\n{'='*70}")
    print(f"PERFORMING {k}-FOLD CROSS-VALIDATION")
    print(f"{'='*70}")

    # Shuffle data
    data_shuffled = data.sample(frac=1, random_state=42).reset_index(drop=True)
    fold_size = len(data_shuffled) // k

    results = []

    for fold_idx in range(k):
        print(f"\n--- Fold {fold_idx + 1}/{k} ---")

        # Split data
        test_start = fold_idx * fold_size
        test_end = test_start + fold_size if fold_idx < k - 1 else len(data_shuffled)

        test_data = data_shuffled.iloc[test_start:test_end].copy()
        train_data = pd.concat([
            data_shuffled.iloc[:test_start],
            data_shuffled.iloc[test_end:]
        ]).copy()

        print(f"  Train size: {len(train_data)}, Test size: {len(test_data)}")

        # Optimize Poisson model parameters on training data
        print(f"  Training Poisson model:")
        best_params = optimize_parameters(train_data, n_sims=n_optimize, verbose=True)
        lambda_s, lambda_r = best_params

        # Run simulations for Poisson model
        print(f"  Evaluating Poisson model on test data ({n_sims} simulations)...")
        sim_poisson = run_simulation_batch(lambda_s, lambda_r, n_matches=n_sims)

        # Run 50-50 baseline
        print(f"  Evaluating 50-50 baseline on test data ({n_sims} simulations)...")
        sim_5050 = baseline_50_50(n_matches=n_sims)

        # Compute metrics
        metrics_poisson = compute_all_metrics(test_data, sim_poisson, model_name=f"Poisson-Fold{fold_idx+1}")
        metrics_5050 = compute_all_metrics(test_data, sim_5050, model_name=f"50-50-Fold{fold_idx+1}")

        results.append({
            'fold': fold_idx + 1,
            'train_data': train_data,
            'test_data': test_data,
            'lambda_s': lambda_s,
            'lambda_r': lambda_r,
            'sim_poisson': sim_poisson,
            'sim_5050': sim_5050,
            'metrics_poisson': metrics_poisson,
            'metrics_5050': metrics_5050
        })

        print(f"  Results:")
        print(f"    Duration Wasserstein - Poisson: {metrics_poisson['duration_wasserstein']:.2f}, 50-50: {metrics_5050['duration_wasserstein']:.2f}")
        print(f"    Games Wasserstein    - Poisson: {metrics_poisson['games_wasserstein']:.2f}, 50-50: {metrics_5050['games_wasserstein']:.2f}")
        print(f"    Tiebreak Prop Diff   - Poisson: {metrics_poisson['tiebreak_prop_diff']*100:.2f}%, 50-50: {metrics_5050['tiebreak_prop_diff']*100:.2f}%")

    return results


# ============= VISUALIZATION =============

def create_comprehensive_plots(cv_results, output_file='comprehensive_validation.png'):
    """
    Create comprehensive visualization with all comparisons.
    """
    # Use middle fold as representative
    avg_fold = cv_results[len(cv_results)//2]

    test_data = avg_fold['test_data']
    sim_poisson = avg_fold['sim_poisson']
    sim_5050 = avg_fold['sim_5050']

    # Create larger, clearer plots
    fig = plt.figure(figsize=(20, 14))
    gs = fig.add_gridspec(3, 3, hspace=0.35, wspace=0.3)

    # Plot 1: Duration distribution
    ax = fig.add_subplot(gs[0, 0])
    bins = np.linspace(0, 250, 35)
    ax.hist(test_data['minutes'], bins=bins, alpha=0.5, label='Real Data',
            density=True, color='black', linewidth=2, edgecolor='black')
    ax.hist(sim_poisson['durations'], bins=bins, alpha=0.6, label='Poisson Model',
            density=True, color='#2E86AB', linewidth=1.5)
    ax.hist(sim_5050['durations'], bins=bins, alpha=0.6, label='50-50 Baseline',
            density=True, color='#A23B72', linewidth=1.5)
    ax.set_xlabel('Match Duration (minutes)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Density', fontsize=12, fontweight='bold')
    ax.set_title('Duration Distribution', fontsize=14, fontweight='bold')
    ax.legend(fontsize=11, loc='upper right')
    ax.grid(True, alpha=0.3, linewidth=0.8)
    ax.tick_params(labelsize=10)

    # Plot 2: Total games distribution
    ax = fig.add_subplot(gs[0, 1])
    bins = range(10, 50)
    ax.hist(test_data['total_games'], bins=bins, alpha=0.5, label='Real Data',
            density=True, color='black', linewidth=2, edgecolor='black')
    ax.hist(sim_poisson['total_games'], bins=bins, alpha=0.6, label='Poisson Model',
            density=True, color='#2E86AB', linewidth=1.5)
    ax.hist(sim_5050['total_games'], bins=bins, alpha=0.6, label='50-50 Baseline',
            density=True, color='#A23B72', linewidth=1.5)
    ax.set_xlabel('Total Games per Match', fontsize=12, fontweight='bold')
    ax.set_ylabel('Density', fontsize=12, fontweight='bold')
    ax.set_title('Total Games Distribution', fontsize=14, fontweight='bold')
    ax.legend(fontsize=11, loc='upper right')
    ax.grid(True, alpha=0.3, linewidth=0.8)
    ax.tick_params(labelsize=10)

    # Plot 3: Number of sets
    ax = fig.add_subplot(gs[0, 2])
    real_sets = test_data['num_sets'].value_counts(normalize=True).sort_index()
    sim_poisson_sets = pd.Series(sim_poisson['num_sets']).value_counts(normalize=True).sort_index()
    sim_5050_sets = pd.Series(sim_5050['num_sets']).value_counts(normalize=True).sort_index()

    all_categories = sorted(set(real_sets.index) | set(sim_poisson_sets.index) | set(sim_5050_sets.index))

    x = np.arange(len(all_categories))
    width = 0.25

    ax.bar(x - width, real_sets.reindex(all_categories, fill_value=0), width,
           label='Real Data', color='black', alpha=0.7, linewidth=1.5, edgecolor='black')
    ax.bar(x, sim_poisson_sets.reindex(all_categories, fill_value=0), width,
           label='Poisson Model', color='#2E86AB', alpha=0.8, linewidth=1.5)
    ax.bar(x + width, sim_5050_sets.reindex(all_categories, fill_value=0), width,
           label='50-50 Baseline', color='#A23B72', alpha=0.8, linewidth=1.5)

    ax.set_xlabel('Number of Sets', fontsize=12, fontweight='bold')
    ax.set_ylabel('Frequency', fontsize=12, fontweight='bold')
    ax.set_title('Match Length Distribution', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(all_categories, fontsize=11)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3, axis='y', linewidth=0.8)
    ax.tick_params(labelsize=10)

    # Plot 4: Wasserstein distance comparison - Duration
    ax = fig.add_subplot(gs[1, 0])
    poisson_vals = [r['metrics_poisson']['duration_wasserstein'] for r in cv_results]
    baseline_vals = [r['metrics_5050']['duration_wasserstein'] for r in cv_results]

    bp = ax.boxplot([poisson_vals, baseline_vals], labels=['Poisson\nModel', '50-50\nBaseline'],
                    patch_artist=True, widths=0.6)
    bp['boxes'][0].set_facecolor('#2E86AB')
    bp['boxes'][1].set_facecolor('#A23B72')
    for element in ['whiskers', 'fliers', 'means', 'medians', 'caps']:
        plt.setp(bp[element], linewidth=2)

    ax.set_ylabel('Wasserstein Distance', fontsize=12, fontweight='bold')
    ax.set_title('Duration: Wasserstein Distance\n(Lower is Better)', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3, linewidth=0.8, axis='y')
    ax.tick_params(labelsize=11)

    # Plot 5: KL divergence comparison - Duration
    ax = fig.add_subplot(gs[1, 1])
    poisson_vals = [r['metrics_poisson']['duration_kl_div'] for r in cv_results]
    baseline_vals = [r['metrics_5050']['duration_kl_div'] for r in cv_results]

    bp = ax.boxplot([poisson_vals, baseline_vals], labels=['Poisson\nModel', '50-50\nBaseline'],
                    patch_artist=True, widths=0.6)
    bp['boxes'][0].set_facecolor('#2E86AB')
    bp['boxes'][1].set_facecolor('#A23B72')
    for element in ['whiskers', 'fliers', 'means', 'medians', 'caps']:
        plt.setp(bp[element], linewidth=2)

    ax.set_ylabel('KL Divergence', fontsize=12, fontweight='bold')
    ax.set_title('Duration: KL Divergence\n(Lower is Better)', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3, linewidth=0.8, axis='y')
    ax.tick_params(labelsize=11)

    # Plot 6: Games Wasserstein
    ax = fig.add_subplot(gs[1, 2])
    poisson_vals = [r['metrics_poisson']['games_wasserstein'] for r in cv_results]
    baseline_vals = [r['metrics_5050']['games_wasserstein'] for r in cv_results]

    bp = ax.boxplot([poisson_vals, baseline_vals], labels=['Poisson\nModel', '50-50\nBaseline'],
                    patch_artist=True, widths=0.6)
    bp['boxes'][0].set_facecolor('#2E86AB')
    bp['boxes'][1].set_facecolor('#A23B72')
    for element in ['whiskers', 'fliers', 'means', 'medians', 'caps']:
        plt.setp(bp[element], linewidth=2)

    ax.set_ylabel('Wasserstein Distance', fontsize=12, fontweight='bold')
    ax.set_title('Total Games: Wasserstein\n(Lower is Better)', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3, linewidth=0.8, axis='y')
    ax.tick_params(labelsize=11)

    # Plot 7: Chi-square for sets
    ax = fig.add_subplot(gs[2, 0])
    poisson_vals = [r['metrics_poisson']['sets_chi2'] for r in cv_results]
    baseline_vals = [r['metrics_5050']['sets_chi2'] for r in cv_results]

    bp = ax.boxplot([poisson_vals, baseline_vals], labels=['Poisson\nModel', '50-50\nBaseline'],
                    patch_artist=True, widths=0.6)
    bp['boxes'][0].set_facecolor('#2E86AB')
    bp['boxes'][1].set_facecolor('#A23B72')
    for element in ['whiskers', 'fliers', 'means', 'medians', 'caps']:
        plt.setp(bp[element], linewidth=2)

    ax.set_ylabel('Chi-Square Statistic', fontsize=12, fontweight='bold')
    ax.set_title('Sets Distribution: Chi-Square\n(Lower is Better)', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3, linewidth=0.8, axis='y')
    ax.tick_params(labelsize=11)

    # Plot 8: Tiebreak proportion difference
    ax = fig.add_subplot(gs[2, 1])
    poisson_vals = [r['metrics_poisson']['tiebreak_prop_diff'] * 100 for r in cv_results]
    baseline_vals = [r['metrics_5050']['tiebreak_prop_diff'] * 100 for r in cv_results]

    bp = ax.boxplot([poisson_vals, baseline_vals], labels=['Poisson\nModel', '50-50\nBaseline'],
                    patch_artist=True, widths=0.6)
    bp['boxes'][0].set_facecolor('#2E86AB')
    bp['boxes'][1].set_facecolor('#A23B72')
    for element in ['whiskers', 'fliers', 'means', 'medians', 'caps']:
        plt.setp(bp[element], linewidth=2)

    ax.set_ylabel('Proportion Difference (%)', fontsize=12, fontweight='bold')
    ax.set_title('Tiebreak: Proportion Diff\n(Lower is Better)', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3, linewidth=0.8, axis='y')
    ax.tick_params(labelsize=11)

    # Plot 9: Parameter estimates across folds
    ax = fig.add_subplot(gs[2, 2])
    lambda_s_vals = [r['lambda_s'] for r in cv_results]
    lambda_r_vals = [r['lambda_r'] for r in cv_results]
    folds = [r['fold'] for r in cv_results]

    ax.plot(folds, lambda_s_vals, 'o-', label='λ_s (server)',
            color='#2E86AB', linewidth=3, markersize=10)
    ax.plot(folds, lambda_r_vals, 's-', label='λ_r (receiver)',
            color='#A23B72', linewidth=3, markersize=10)
    ax.set_xlabel('Fold', fontsize=12, fontweight='bold')
    ax.set_ylabel('Rate (points/sec)', fontsize=12, fontweight='bold')
    ax.set_title('Parameter Estimates Across Folds', fontsize=13, fontweight='bold')
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3, linewidth=0.8)
    ax.tick_params(labelsize=10)

    plt.suptitle('Comprehensive Model Validation with Cross-Validation',
                 fontsize=18, fontweight='bold', y=0.995)

    plt.savefig(output_file, dpi=200, bbox_inches='tight')
    print(f"\nComprehensive visualization saved to '{output_file}'")

    return fig


def create_metrics_table(cv_results, output_file='validation_metrics.csv'):
    """
    Create detailed metrics table.
    """
    all_metrics = []

    for result in cv_results:
        # Poisson model
        m = result['metrics_poisson'].copy()
        m['Model'] = 'Poisson'
        m['Fold'] = result['fold']
        m['lambda_s'] = result['lambda_s']
        m['lambda_r'] = result['lambda_r']
        all_metrics.append(m)

        # 50-50 baseline
        m = result['metrics_5050'].copy()
        m['Model'] = '50-50'
        m['Fold'] = result['fold']
        m['lambda_s'] = 0.0165
        m['lambda_r'] = 0.0165
        all_metrics.append(m)

    df = pd.DataFrame(all_metrics)

    # Reorder columns
    first_cols = ['Model', 'Fold', 'lambda_s', 'lambda_r']
    other_cols = [c for c in df.columns if c not in first_cols]
    df = df[first_cols + other_cols]

    df.to_csv(output_file, index=False, float_format='%.6f')
    print(f"Detailed metrics table saved to '{output_file}'")

    # Print summary statistics
    print("\n" + "="*70)
    print("SUMMARY STATISTICS (Averaged Across Folds)")
    print("="*70)

    summary = df.groupby('Model').agg({
        'duration_wasserstein': ['mean', 'std'],
        'duration_kl_div': ['mean', 'std'],
        'games_wasserstein': ['mean', 'std'],
        'sets_chi2': ['mean', 'std'],
        'tiebreak_prop_diff': ['mean', 'std']
    })

    print(summary.to_string())
    print()

    return df


# ============= MAIN EXECUTION =============

if __name__ == "__main__":
    print("="*70)
    print("COMPREHENSIVE TENNIS MODEL VALIDATION")
    print("Multi-year data with cross-validation and baseline comparison")
    print("="*70)

    # Load all ATP data
    print("\n[1/4] Loading all ATP match data...")
    all_data = load_all_atp_data('tennis_atp', years_range=(2010, 2024), best_of=3)

    # Perform cross-validation
    print("\n[2/4] Running cross-validation with parameter optimization...")
    cv_results = k_fold_cross_validation(all_data, k=5, n_sims=500, n_optimize=200)

    # Create comprehensive plots
    print("\n[3/4] Creating comprehensive visualizations...")
    create_comprehensive_plots(cv_results, output_file='comprehensive_validation.png')

    # Create metrics table
    print("\n[4/4] Creating detailed metrics table...")
    metrics_df = create_metrics_table(cv_results, output_file='validation_metrics.csv')

    print("\n" + "="*70)
    print("VALIDATION COMPLETE!")
    print("="*70)
    print("\nOutputs saved:")
    print("  - comprehensive_validation.png (9-panel visualization)")
    print("  - validation_metrics.csv (detailed metrics table)")

    # Print key findings
    print("\n" + "="*70)
    print("KEY FINDINGS")
    print("="*70)

    poisson_metrics = metrics_df[metrics_df['Model'] == 'Poisson']
    fiftyfifty_metrics = metrics_df[metrics_df['Model'] == '50-50']

    print(f"\nDuration Wasserstein Distance (mean ± std):")
    print(f"  Poisson Model:  {poisson_metrics['duration_wasserstein'].mean():.2f} ± {poisson_metrics['duration_wasserstein'].std():.2f}")
    print(f"  50-50 Baseline: {fiftyfifty_metrics['duration_wasserstein'].mean():.2f} ± {fiftyfifty_metrics['duration_wasserstein'].std():.2f}")

    print(f"\nGames Wasserstein Distance (mean ± std):")
    print(f"  Poisson Model:  {poisson_metrics['games_wasserstein'].mean():.2f} ± {poisson_metrics['games_wasserstein'].std():.2f}")
    print(f"  50-50 Baseline: {fiftyfifty_metrics['games_wasserstein'].mean():.2f} ± {fiftyfifty_metrics['games_wasserstein'].std():.2f}")

    print(f"\nTiebreak Proportion Difference (mean ± std):")
    print(f"  Poisson Model:  {poisson_metrics['tiebreak_prop_diff'].mean()*100:.2f}% ± {poisson_metrics['tiebreak_prop_diff'].std()*100:.2f}%")
    print(f"  50-50 Baseline: {fiftyfifty_metrics['tiebreak_prop_diff'].mean()*100:.2f}% ± {fiftyfifty_metrics['tiebreak_prop_diff'].std()*100:.2f}%")

    # Average parameters
    print(f"\nAverage Optimized Parameters:")
    print(f"  λ_s = {poisson_metrics['lambda_s'].mean():.5f} ± {poisson_metrics['lambda_s'].std():.5f} points/sec")
    print(f"  λ_r = {poisson_metrics['lambda_r'].mean():.5f} ± {poisson_metrics['lambda_r'].std():.5f} points/sec")
    avg_srv_adv = poisson_metrics['lambda_s'].mean() / (poisson_metrics['lambda_s'].mean() + poisson_metrics['lambda_r'].mean())
    print(f"  Server advantage: {avg_srv_adv*100:.1f}%")

    # Determine best model
    print(f"\n" + "="*70)
    print("MODEL RANKING (by average Wasserstein distance on duration)")
    print("="*70)

    model_scores = {
        'Poisson': poisson_metrics['duration_wasserstein'].mean(),
        '50-50': fiftyfifty_metrics['duration_wasserstein'].mean()
    }

    ranked = sorted(model_scores.items(), key=lambda x: x[1])
    for i, (model, score) in enumerate(ranked, 1):
        print(f"{i}. {model}: {score:.2f}")

    print("\n" + "="*70)
