import numpy as np
import matplotlib.pyplot as plt

# ============= PARAMETERS =============
np.random.seed(42)

# Scoring rates
lambda_s = 0.65 / 30  # Server wins point at this rate (points per second)
lambda_r = 0.35 / 30  # Receiver wins point at this rate
lam = lambda_s + lambda_r  # Total rate

# Simulation parameters
T = 300  # Maximum time for a game (seconds)
n_games = 10000  # Number of games to simulate
dt = 0.1  # Time step (seconds)

times = np.arange(0, T + dt, dt)

# ============= STATE DEFINITIONS =============
# Point values: 0='0', 1='15', 2='30', 3='40'
# States: (server_points, receiver_points)
# Special states: 'deuce', 'ad_s', 'ad_r', 'win_s', 'win_r'

# Track statistics
count_deuce = np.zeros_like(times)  # Times we're at deuce
count_active = np.zeros_like(times)  # Games still active
count_adv_s = np.zeros_like(times)   # Times at advantage server
count_adv_r = np.zeros_like(times)   # Times at advantage receiver

# ============= SIMULATION =============
for game_idx in range(n_games):
    # Initial state: 0-0
    server_pts = 0
    receiver_pts = 0
    state = 'playing'  # 'playing', 'deuce', 'ad_s', 'ad_r', 'finished'
    
    for i, t in enumerate(times):
        if state == 'finished':
            break
            
        # Record current state
        count_active[i] += 1
        if state == 'deuce':
            count_deuce[i] += 1
        elif state == 'ad_s':
            count_adv_s[i] += 1
        elif state == 'ad_r':
            count_adv_r[i] += 1
        
        # Determine if a point is scored in this time step
        if np.random.rand() < lambda_s * dt:
            # Server wins the point
            if state == 'playing':
                if server_pts < 3:
                    server_pts += 1
                elif server_pts == 3:
                    # Server at 40
                    if receiver_pts < 3:
                        # Server wins game
                        state = 'finished'
                    elif receiver_pts == 3:
                        # Go to advantage server
                        state = 'ad_s'
            elif state == 'deuce':
                state = 'ad_s'
            elif state == 'ad_s':
                # Server wins game
                state = 'finished'
            elif state == 'ad_r':
                # Back to deuce
                state = 'deuce'
                
        elif np.random.rand() < lambda_r * dt:
            # Receiver wins the point
            if state == 'playing':
                if receiver_pts < 3:
                    receiver_pts += 1
                elif receiver_pts == 3:
                    # Receiver at 40
                    if server_pts < 3:
                        # Receiver wins game
                        state = 'finished'
                    elif server_pts == 3:
                        # Go to advantage receiver
                        state = 'ad_r'
            elif state == 'deuce':
                state = 'ad_r'
            elif state == 'ad_r':
                # Receiver wins game
                state = 'finished'
            elif state == 'ad_s':
                # Back to deuce
                state = 'deuce'
        
        # Check if we just reached deuce from (3,3) in playing state
        if state == 'playing' and server_pts == 3 and receiver_pts == 3:
            state = 'deuce'

# ============= COMPUTE PROBABILITIES =============
prob_deuce = count_deuce / count_active  # P(deuce | game still active)
prob_adv_s = count_adv_s / count_active
prob_adv_r = count_adv_r / count_active
fraction_active = count_active / n_games

# ============= PLOTTING =============
fig, axes = plt.subplots(2, 2, figsize=(12, 10))

# Plot 1: Probability of being at Deuce (given game active)
axes[0, 0].plot(times, prob_deuce, 'b-', linewidth=2, label='P(Deuce | Active)')
axes[0, 0].set_xlabel('Time (seconds)', fontsize=11)
axes[0, 0].set_ylabel('Probability', fontsize=11)
axes[0, 0].set_title('Probability of Deuce State', fontsize=12, fontweight='bold')
axes[0, 0].grid(True, alpha=0.3)
axes[0, 0].legend()
axes[0, 0].set_xlim([0, 200])

# Plot 2: Advantage states
axes[0, 1].plot(times, prob_adv_s, 'r-', linewidth=2, label='P(Ad-Server | Active)')
axes[0, 1].plot(times, prob_adv_r, 'orange', linewidth=2, label='P(Ad-Receiver | Active)')
axes[0, 1].set_xlabel('Time (seconds)', fontsize=11)
axes[0, 1].set_ylabel('Probability', fontsize=11)
axes[0, 1].set_title('Advantage States', fontsize=12, fontweight='bold')
axes[0, 1].grid(True, alpha=0.3)
axes[0, 1].legend()
axes[0, 1].set_xlim([0, 200])

# Plot 3: Fraction of games still active
axes[1, 0].plot(times, fraction_active, 'g-', linewidth=2)
axes[1, 0].set_xlabel('Time (seconds)', fontsize=11)
axes[1, 0].set_ylabel('Fraction of Games', fontsize=11)
axes[1, 0].set_title('Games Still Active (Not Yet Won)', fontsize=12, fontweight='bold')
axes[1, 0].grid(True, alpha=0.3)
axes[1, 0].set_xlim([0, 200])

# Plot 4: Score distribution at t=60s (example snapshot)
t_snapshot = 60  # seconds
idx = int(t_snapshot / dt)
if idx < len(times):
    # Create a simple visualization of state probabilities
    states_labels = ['Deuce', 'Adv-S', 'Adv-R', 'Finished']
    probs_snapshot = [
        prob_deuce[idx],
        prob_adv_s[idx],
        prob_adv_r[idx],
        1 - fraction_active[idx]
    ]
    
    colors = ['blue', 'red', 'orange', 'gray']
    axes[1, 1].bar(states_labels, probs_snapshot, color=colors, alpha=0.7, edgecolor='black')
    axes[1, 1].set_ylabel('Probability', fontsize=11)
    axes[1, 1].set_title(f'State Distribution at t={t_snapshot}s', fontsize=12, fontweight='bold')
    axes[1, 1].grid(True, alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig('tennis_simulation.png', bbox_inches='tight')
plt.show()

# ============= SUMMARY STATISTICS =============
print(f"\n{'='*60}")
print(f"TENNIS GAME SIMULATION RESULTS")
print(f"{'='*60}")
print(f"Number of games simulated: {n_games:,}")
print(f"Server scoring rate: λ_s = {lambda_s:.4f} points/sec")
print(f"Receiver scoring rate: λ_r = {lambda_r:.4f} points/sec")
print(f"Server advantage: {lambda_s/lam*100:.1f}% vs {lambda_r/lam*100:.1f}%")
print(f"\nKey findings:")
print(f"- Peak deuce probability: {np.max(prob_deuce):.3f} at t={times[np.argmax(prob_deuce)]:.1f}s")
print(f"- Games finished by 60s: {(1-fraction_active[int(60/dt)])*100:.1f}%")
print(f"- Games finished by 120s: {(1-fraction_active[int(120/dt)])*100:.1f}%")
print(f"- Mean time to finish: ~{times[np.where(fraction_active < 0.5)[0][0]]:.1f}s (median)")
print(f"{'='*60}\n")