import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import wasserstein_distance, chi2_contingency
from scipy.spatial.distance import jensenshannon
from collections import Counter
import warnings

from validate_model import load_atp_data, run_simulation_batch

warnings.filterwarnings("ignore")


def calculate_kl_divergence(p, q, epsilon=1e-10):
    # Add small epsilon to avoid log(0)
    p = np.array(p) + epsilon
    q = np.array(q) + epsilon

    # Normalize to ensure they sum to 1
    p = p / np.sum(p)
    q = q / np.sum(q)

    return np.sum(p * np.log(p / q))


def js_divergence(p, q):
    return jensenshannon(p, q) ** 2


def proportion_test(x1, n1, x2, n2):
    p1 = x1 / n1
    p2 = x2 / n2

    # Pooled proportion
    p_pool = (x1 + x2) / (n1 + n2)

    # Standard error
    se = np.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))

    # Z statistic
    z_stat = (p1 - p2) / se if se > 0 else 0

    # P-value (two-tailed)
    p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))

    # Effect size (Cohen's h)
    effect_size = 2 * (np.arcsin(np.sqrt(p1)) - np.arcsin(np.sqrt(p2)))

    return z_stat, p_value, effect_size


def calculate_distributional_metrics(real_data, sim_data, metric_name):
    real_vals = np.array(real_data)
    sim_vals = np.array(sim_data)

    metrics = {
        "metric_name": metric_name,
        "real_mean": np.mean(real_vals),
        "sim_mean": np.mean(sim_vals),
        "real_std": np.std(real_vals),
        "sim_std": np.std(sim_vals),
        "mean_difference": np.mean(sim_vals) - np.mean(real_vals),
        "std_difference": np.std(sim_vals) - np.std(real_vals),
        "wasserstein_distance": wasserstein_distance(real_vals, sim_vals),
        "ks_statistic": stats.ks_2samp(real_vals, sim_vals)[0],
        "ks_pvalue": stats.ks_2samp(real_vals, sim_vals)[1],
        "mann_whitney_u": stats.mannwhitneyu(
            real_vals, sim_vals, alternative="two-sided"
        )[0],
        "mann_whitney_p": stats.mannwhitneyu(
            real_vals, sim_vals, alternative="two-sided"
        )[1],
    }

    return metrics


def calculate_categorical_metrics(real_counts, sim_counts, category_name):
    if isinstance(real_counts, dict):
        real_counts = Counter(real_counts)
    if isinstance(sim_counts, dict):
        sim_counts = Counter(sim_counts)

    all_categories = set(real_counts.keys()) | set(sim_counts.keys())
    real_array = np.array([real_counts.get(cat, 0) for cat in sorted(all_categories)])
    sim_array = np.array([sim_counts.get(cat, 0) for cat in sorted(all_categories)])

    real_props = real_array / np.sum(real_array)
    sim_props = sim_array / np.sum(sim_array)

    # Chi-squared test
    contingency_table = np.array([real_array, sim_array])
    if np.min(contingency_table) >= 5:  # Check minimum expected frequency
        chi2_stat, chi2_p, dof, expected = chi2_contingency(contingency_table)
    else:
        chi2_stat, chi2_p = np.nan, np.nan

    metrics = {
        "category_name": category_name,
        "categories": sorted(all_categories),
        "real_proportions": real_props,
        "sim_proportions": sim_props,
        "kl_divergence": calculate_kl_divergence(real_props, sim_props),
        "js_divergence": js_divergence(real_props, sim_props),
        "chi2_statistic": chi2_stat,
        "chi2_pvalue": chi2_p,
        "total_variation_distance": 0.5 * np.sum(np.abs(real_props - sim_props)),
    }

    return metrics


def analyze_set_score_patterns(real_data, sim_results):
    def extract_set_patterns(data, is_simulation=False):
        patterns = []

        if is_simulation:
            for result in data:
                for set_score in result:
                    g1, g2 = set_score
                    patterns.append(f"{max(g1, g2)}-{min(g1, g2)}")
        else:
            for _, row in data.iterrows():
                parsed_score = row.get("parsed_score")
                if parsed_score is not None and len(parsed_score) > 0:
                    for g1, g2 in parsed_score:
                        patterns.append(f"{max(g1, g2)}-{min(g1, g2)}")

        return Counter(patterns)

    real_patterns = extract_set_patterns(real_data, is_simulation=False)
    sim_patterns = extract_set_patterns(sim_results["set_scores"], is_simulation=True)

    return calculate_categorical_metrics(
        real_patterns, sim_patterns, "Set Score Patterns"
    )


def run_comprehensive_analysis():
    print("=" * 80)
    print("COMPREHENSIVE QUANTITATIVE METRICS ANALYSIS")
    print("=" * 80)

    print("\n[1/4] Loading ATP match data...")
    real_data = load_atp_data("atp_matches_2024.csv")

    print("\n[2/4] Running simulations...")
    # These are the optimal parameters obtained from model validation
    lambda_s_opt = 0.01100
    lambda_r_opt = 0.00900

    print(f"  Using λ_s = {lambda_s_opt:.5f}, λ_r = {lambda_r_opt:.5f}")
    print("  Simulating 3000 matches (this may take 2-3 minutes)...")

    sim_results = run_simulation_batch(lambda_s_opt, lambda_r_opt, n_matches=3000)

    print("\n[3/4] Calculating quantitative metrics...")

    # ========== DISTRIBUTIONAL METRICS ==========
    distributional_metrics = []

    # Match duration
    duration_metrics = calculate_distributional_metrics(
        real_data["minutes"].values,
        sim_results["durations"],
        "Match Duration (minutes)",
    )
    distributional_metrics.append(duration_metrics)

    # Total games per match
    games_metrics = calculate_distributional_metrics(
        real_data["total_games"].values,
        sim_results["total_games"],
        "Total Games per Match",
    )
    distributional_metrics.append(games_metrics)

    # ========== PROPORTION TESTS ==========
    proportion_tests = []

    # Tiebreak frequency
    real_tb_count = real_data["had_tiebreak"].sum()
    real_total = len(real_data)
    sim_tb_count = sum(sim_results["had_tiebreak"])
    sim_total = len(sim_results["had_tiebreak"])

    tb_z, tb_p, tb_effect = proportion_test(
        real_tb_count, real_total, sim_tb_count, sim_total
    )

    proportion_tests.append(
        {
            "test_name": "Tiebreak Frequency",
            "real_proportion": real_tb_count / real_total,
            "sim_proportion": sim_tb_count / sim_total,
            "difference": (sim_tb_count / sim_total) - (real_tb_count / real_total),
            "z_statistic": tb_z,
            "p_value": tb_p,
            "effect_size": tb_effect,
            "significant": tb_p < 0.05,
        }
    )

    # ========== CATEGORICAL DISTRIBUTIONS ==========
    categorical_metrics = []

    # Number of sets distribution
    real_sets_dist = real_data["num_sets"].value_counts()
    sim_sets_dist = pd.Series(sim_results["num_sets"]).value_counts()

    sets_metrics = calculate_categorical_metrics(
        real_sets_dist.to_dict(), sim_sets_dist.to_dict(), "Number of Sets per Match"
    )
    categorical_metrics.append(sets_metrics)

    # Set score patterns
    print("  Analyzing set score patterns...")
    set_patterns_metrics = analyze_set_score_patterns(real_data, sim_results)
    categorical_metrics.append(set_patterns_metrics)

    print("\n[4/4] Generating results tables...")

    # Table 1: Distributional Metrics
    print("\n" + "=" * 80)
    print("TABLE 1: DISTRIBUTIONAL METRICS")
    print("=" * 80)

    dist_df = pd.DataFrame(distributional_metrics)
    print(
        f"{'Metric':<25} {'Real Mean':<12} {'Sim Mean':<12} {'Difference':<12} {'Wasserstein':<12} {'KS p-value':<12}"
    )
    print("-" * 85)

    for _, row in dist_df.iterrows():
        print(
            f"{row['metric_name']:<25} {row['real_mean']:<12.2f} {row['sim_mean']:<12.2f} "
            f"{row['mean_difference']:<12.2f} {row['wasserstein_distance']:<12.3f} {row['ks_pvalue']:<12.4f}"
        )

    # Table 2: Proportion Tests
    print("\n" + "=" * 80)
    print("TABLE 2: PROPORTION TESTS")
    print("=" * 80)

    prop_df = pd.DataFrame(proportion_tests)
    print(
        f"{'Test':<20} {'Real %':<10} {'Sim %':<10} {'Diff %':<10} {'Z-stat':<10} {'p-value':<10} {'Significant':<12}"
    )
    print("-" * 82)

    for _, row in prop_df.iterrows():
        print(
            f"{row['test_name']:<20} {row['real_proportion'] * 100:<10.2f} {row['sim_proportion'] * 100:<10.2f} "
            f"{row['difference'] * 100:<10.2f} {row['z_statistic']:<10.3f} {row['p_value']:<10.4f} "
            f"{'Yes' if row['significant'] else 'No':<12}"
        )

    # Table 3: Categorical Distributions
    print("\n" + "=" * 80)
    print("TABLE 3: CATEGORICAL DISTRIBUTION TESTS")
    print("=" * 80)

    print(
        f"{'Category':<25} {'KL Divergence':<15} {'JS Divergence':<15} {'Chi² p-value':<15} {'TV Distance':<15}"
    )
    print("-" * 85)

    for metrics in categorical_metrics:
        print(
            f"{metrics['category_name']:<25} {metrics['kl_divergence']:<15.4f} "
            f"{metrics['js_divergence']:<15.4f} {metrics['chi2_pvalue']:<15.4f} "
            f"{metrics['total_variation_distance']:<15.4f}"
        )

    # Table 4: Detailed Set Distribution
    print("\n" + "=" * 80)
    print("TABLE 4: NUMBER OF SETS DISTRIBUTION")
    print("=" * 80)

    sets_metrics = categorical_metrics[0]  # Number of sets is first categorical metric
    print(
        f"{'Sets':<8} {'Real Count':<12} {'Real %':<10} {'Sim Count':<12} {'Sim %':<10} {'Difference':<12}"
    )
    print("-" * 70)

    real_total = sum(real_sets_dist.values)
    sim_total = sum(sim_sets_dist.values)

    for i, category in enumerate(sets_metrics["categories"]):
        real_prop = sets_metrics["real_proportions"][i]
        sim_prop = sets_metrics["sim_proportions"][i]
        real_count = int(real_prop * real_total)
        sim_count = int(sim_prop * sim_total)

        print(
            f"{category:<8} {real_count:<12} {real_prop * 100:<10.2f} {sim_count:<12} "
            f"{sim_prop * 100:<10.2f} {(sim_prop - real_prop) * 100:<12.2f}"
        )

    # Save results
    print("\n" + "=" * 80)
    print("SAVING DETAILED RESULTS")
    print("=" * 80)

    # Save distributional metrics
    dist_df.to_csv("distributional_metrics.csv", index=False)

    # Save proportion tests
    prop_df.to_csv("proportion_tests.csv", index=False)

    # Save categorical metrics summary
    cat_summary = []
    for metrics in categorical_metrics:
        cat_summary.append(
            {
                "category_name": metrics["category_name"],
                "kl_divergence": metrics["kl_divergence"],
                "js_divergence": metrics["js_divergence"],
                "chi2_statistic": metrics["chi2_statistic"],
                "chi2_pvalue": metrics["chi2_pvalue"],
                "total_variation_distance": metrics["total_variation_distance"],
            }
        )

    pd.DataFrame(cat_summary).to_csv("categorical_metrics.csv", index=False)

    print("Results saved to:")
    print("  - distributional_metrics.csv")
    print("  - proportion_tests.csv")
    print("  - categorical_metrics.csv")

    print("\n" + "=" * 80)
    print("SUMMARY OF FINDINGS")
    print("=" * 80)

    print("\nKey Model Performance Metrics:")
    print(
        f"  Duration Wasserstein Distance: {duration_metrics['wasserstein_distance']:.2f} minutes"
    )
    print(
        f"  Games Wasserstein Distance: {duration_metrics['wasserstein_distance']:.2f} games"
    )
    print(
        f"  Tiebreak Frequency Error: {abs(proportion_tests[0]['difference']) * 100:.2f}%"
    )
    print(f"  Sets Distribution KL Divergence: {sets_metrics['kl_divergence']:.4f}")

    # Statistical significance
    significant_tests = [test for test in proportion_tests if test["significant"]]
    print("\nStatistical Significance:")
    print(
        f"  {len(significant_tests)}/{len(proportion_tests)} proportion tests significant (p < 0.05)"
    )

    non_sig_ks = [
        metric for metric in distributional_metrics if metric["ks_pvalue"] > 0.05
    ]
    print(
        f"  {len(non_sig_ks)}/{len(distributional_metrics)} distributions not significantly different (KS test p > 0.05)"
    )

    return {
        "distributional_metrics": distributional_metrics,
        "proportion_tests": proportion_tests,
        "categorical_metrics": categorical_metrics,
        "lambda_s": lambda_s_opt,
        "lambda_r": lambda_r_opt,
    }


if __name__ == "__main__":
    results = run_comprehensive_analysis()

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE!")
    print("=" * 80)
