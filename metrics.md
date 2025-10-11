# Tennis Simulation Model - Quantitative Metrics Analysis

## Model Parameters Used

- Server scoring rate (λ_s): 0.01100 points/second
- Receiver scoring rate (λ_r): 0.00900 points/second
- Number of simulated matches: 3,000
- Number of real ATP matches: 2,433

## 1. Distributional Metrics

| Metric                   | Real Mean | Sim Mean | Difference | Real Std | Sim Std | Wasserstein Distance | KS p-value | Significant Difference |
| ------------------------ | --------- | -------- | ---------- | -------- | ------- | -------------------- | ---------- | ---------------------- |
| Match Duration (minutes) | 107.81    | 112.31   | +4.50      | 33.19    | 32.10   | 4.91                 | < 0.001    | ✓ Yes                  |
| Total Games per Match    | 23.19     | 21.84    | -1.35      | 6.05     | 5.74    | 1.45                 | < 0.001    | ✓ Yes                  |

## 2. Proportion Tests

| Test               | Real % | Sim %  | Difference % | Z-statistic | p-value | Effect Size | Significant |
| ------------------ | ------ | ------ | ------------ | ----------- | ------- | ----------- | ----------- |
| Tiebreak Frequency | 38.59% | 20.17% | -18.43%      | 14.98       | < 0.001 | 0.41        | ✓ Yes       |

## 3. Categorical Distribution Tests

| Category                 | KL Divergence | JS Divergence | Total Variation Distance | Assessment          |
| ------------------------ | ------------- | ------------- | ------------------------ | ------------------- |
| Number of Sets per Match | 0.075         | 0.002         | 0.005                    | Very good agreement |
| Set Score Patterns       | 0.236         | 0.023         | 0.148                    | Moderate difference |
