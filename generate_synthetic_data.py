"""
Synthetic Psychoacoustic Data Generator - Stage 2
Generates realistic synthetic JND (Just Noticeable Difference) data
for 2×2 Full Factorial Design: Frequency × ISI

Experimental Design:
- Factor A: Frequency (250 Hz, 1000 Hz) - SPECTRAL
- Factor B: ISI (200 ms, 1000 ms) - TEMPORAL
- Replications: 2
- Total observations: 8 (4 treatments × 2 replications)

Psychoacoustic Assumptions:
1. JND is frequency-dependent (Weber's Law)
2. JND increases with longer ISI (auditory memory decay)
3. Individual variability around mean JND
4. All values within 0.5-3.5 dB range (typical for healthy hearing)
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Psychoacoustic baseline JND values (dB SPL)
# Based on research literature for pure tones
BASE_JND = {
    250: 1.8,    # Lower frequency - slightly higher JND
    1000: 1.2    # Mid-high frequency - lower JND (most sensitive)
}

# ISI effects on JND (higher ISI = worse memory = higher JND threshold)
ISI_EFFECT = {
    200: 0.0,    # Shorter ISI - baseline
    1000: 0.8    # Longer ISI - JND increases by ~0.8 dB
}

# Realistic individual variability (standard deviation)
INDIVIDUAL_VARIABILITY = 0.2  # ±0.2 dB

# Participant ID and metadata
PARTICIPANT_ID = "P" + str(int(datetime.now().timestamp())) + "synthetic"
PARTICIPANT_NAME = "Synthetic_Participant"
EXPERIMENT_DATE = datetime.now().date()

def generate_jnd_value(frequency, isi, replication):
    """
    Generate a realistic JND measurement based on the experimental factors.
    
    Args:
        frequency: 250 or 1000 Hz
        isi: 200 or 1000 ms
        replication: 1 or 2
    
    Returns:
        JND value in dB
    """
    # Base JND for frequency
    base = BASE_JND.get(frequency, 1.5)
    
    # ISI effect (auditory memory decay)
    isi_effect = ISI_EFFECT.get(isi, 0.0)
    
    # Replication-specific variability
    # Replications show slight systematic variation (learning/fatigue)
    replication_effect = (replication - 1) * 0.1
    
    # Random individual variability
    random_variation = np.random.normal(0, INDIVIDUAL_VARIABILITY)
    
    # Calculate final JND
    jnd = base + isi_effect + replication_effect + random_variation
    
    # Bound to realistic range
    jnd = np.clip(jnd, 0.5, 3.5)
    
    return jnd

def generate_trial_history(frequency, isi, replication):
    """
    Generate synthetic trial-by-trial data for a single block.
    Models an adaptive staircase procedure.
    
    Returns:
        List of trial records
    """
    trials = []
    target_reversals = 6
    discard_reversals = 2
    usable_reversals = target_reversals - discard_reversals
    
    # Expected threshold for this condition
    expected_threshold = generate_jnd_value(frequency, isi, replication)
    
    # Simulate staircase convergence
    current_delta = 5.0  # Start at 5 dB
    correct_streak = 0
    reversals = []
    last_direction = None
    first_error = False
    step_size = 1.0  # Large step initially
    trial_count = 0
    
    while len(reversals) < target_reversals and trial_count < 40:
        trial_count += 1
        direction = None  # Initialize direction
        
        # Probability of correct response (logistic function around threshold)
        probability_correct = 1.0 / (1.0 + np.exp(-5 * (current_delta - expected_threshold)))
        correct = np.random.random() < probability_correct
        
        # Staircase logic
        if not first_error:
            if correct:
                correct_streak += 1
                if correct_streak >= 3:
                    current_delta = max(0.5, current_delta - step_size)
                    direction = 'down'
                    correct_streak = 0
            else:
                first_error = True
                step_size = 0.5  # Fine step
                current_delta = min(12.0, current_delta + step_size)
                direction = 'up'
                correct_streak = 0
        else:
            if correct:
                correct_streak += 1
                if correct_streak >= 3:
                    current_delta = max(0.5, current_delta - step_size)
                    direction = 'down'
                    correct_streak = 0
            else:
                current_delta = min(12.0, current_delta + step_size)
                direction = 'up'
                correct_streak = 0
        
        # Detect reversal
        if direction and last_direction and direction != last_direction:
            reversals.append({
                'trial': trial_count,
                'deltaI': current_delta,
                'direction': direction
            })
        
        if direction:
            last_direction = direction
        
        trials.append({
            'trial_number': trial_count,
            'delta_i': round(current_delta, 1),
            'response': 1 if correct else 2,  # 1=correct, 2=incorrect
            'direction': direction if direction else 'none'
        })
    
    return trials, reversals, trial_count

def generate_synthetic_dataset():
    """
    Generate complete synthetic dataset for one participant.
    
    Returns:
        DataFrame with columns matching the expected experimental data
    """
    data_records = []
    
    # Experimental design
    frequencies = [250, 1000]
    isi_values = [200, 1000]
    replications = [1, 2]
    
    # Generate block order (randomized)
    blocks = []
    for rep in replications:
        for freq in frequencies:
            for isi in isi_values:
                blocks.append({
                    'frequency': freq,
                    'isi': isi,
                    'replication': rep
                })
    
    # Simulate participant completing blocks in randomized order
    block_order = np.random.permutation(len(blocks))
    
    for block_idx, block_slot in enumerate(block_order):
        block = blocks[block_slot]
        frequency = block['frequency']
        isi = block['isi']
        replication = block['replication']
        
        # Generate threshold for this block
        threshold = generate_jnd_value(frequency, isi, replication)
        
        # Generate trial history
        trials, reversals, total_trials = generate_trial_history(frequency, isi, replication)
        
        # Calculate usable reversals (discard first 2)
        usable_reversals = reversals[2:] if len(reversals) > 2 else []
        calculated_threshold = (
            np.mean([r['deltaI'] for r in usable_reversals])
            if usable_reversals else threshold
        )
        
        # Create block record
        record = {
            'participant_id': PARTICIPANT_ID,
            'participant_name': PARTICIPANT_NAME,
            'block_number': block_idx + 1,
            'frequency_hz': frequency,
            'isi_ms': isi,
            'replication': replication,
            'treatment_combination': f"Freq{frequency}_ISI{isi}",
            'threshold_db': round(calculated_threshold, 3),
            'total_trials': total_trials,
            'total_reversals': len(reversals),
            'usable_reversals': len(usable_reversals),
            'experiment_date': EXPERIMENT_DATE,
            'block_start_time': (EXPERIMENT_DATE + timedelta(minutes=30 + block_idx*15)).isoformat(),
            'tone_type': 'sine',  # Pure sine waves for JND
            'session_id': 'synthetic_001'
        }
        data_records.append(record)
    
    return pd.DataFrame(data_records)

def save_synthetic_data(df, filename='synthetic_psychoacoustic_data_isi.csv'):
    """Save synthetic dataset to CSV."""
    df.to_csv(filename, index=False)
    print(f"\n✓ Synthetic data saved to: {filename}")
    print(f"✓ Participant ID: {PARTICIPANT_ID}")
    print(f"✓ Total records: {len(df)}")
    
    return df

def print_summary_statistics(df):
    """Print summary statistics of the synthetic data."""
    print("\n" + "=" * 70)
    print("SYNTHETIC PSYCHOACOUSTIC DATA - SUMMARY STATISTICS")
    print("=" * 70)
    
    # Overall statistics
    print(f"\nOVERALL JND STATISTICS:")
    print(f"  Mean JND: {df['threshold_db'].mean():.3f} dB")
    print(f"  Std Dev:  {df['threshold_db'].std():.3f} dB")
    print(f"  Min:      {df['threshold_db'].min():.3f} dB")
    print(f"  Max:      {df['threshold_db'].max():.3f} dB")
    
    # By frequency
    print(f"\nBY FREQUENCY:")
    for freq in sorted(df['frequency_hz'].unique()):
        subset = df[df['frequency_hz'] == freq]['threshold_db']
        print(f"  {freq} Hz: {subset.mean():.3f} ± {subset.std():.3f} dB")
    
    # By ISI
    print(f"\nBY ISI:")
    for isi in sorted(df['isi_ms'].unique()):
        subset = df[df['isi_ms'] == isi]['threshold_db']
        print(f"  {isi} ms: {subset.mean():.3f} ± {subset.std():.3f} dB")
    
    # By treatment combination
    print(f"\nBY TREATMENT COMBINATION (Frequency × ISI):")
    for treatment in sorted(df['treatment_combination'].unique()):
        subset = df[df['treatment_combination'] == treatment]['threshold_db']
        print(f"  {treatment}: {subset.mean():.3f} ± {subset.std():.3f} dB (n={len(subset)})")
    
    print("\n" + "=" * 70)
    print("DATA INTERPRETATION:")
    print("=" * 70)
    print("Expected Pattern (Auditory Memory Decay):")
    print("  - Longer ISI (1000 ms) should show HIGHER JND (worse discrimination)")
    print("  - Shorter ISI (200 ms) should show LOWER JND (better discrimination)")
    print("  - ISI effect tests the auditory temporal window")
    print("\nExpected Frequency Effects:")
    print("  - Individual variation is expected")
    print("  - Both frequencies are within normal hearing range")
    print("=" * 70)

def print_design_matrix(df):
    """Print the design matrix showing all factor levels."""
    print("\n" + "=" * 70)
    print("FACTORIAL DESIGN MATRIX")
    print("=" * 70)
    
    print("\nFull 2×2 Factorial Design with Replications:")
    print("\nTreatment Combinations and JND Thresholds:")
    print("-" * 70)
    
    for freq in sorted(df['frequency_hz'].unique()):
        for isi in sorted(df['isi_ms'].unique()):
            subset = df[(df['frequency_hz'] == freq) & (df['isi_ms'] == isi)]
            thresholds = subset['threshold_db'].values
            print(f"Frequency={freq:4d} Hz, ISI={isi:4d} ms: {thresholds[0]:.3f}, {thresholds[1]:.3f} dB")
    
    print("-" * 70)
    print("✓ Design Structure: 2 Frequencies × 2 ISI Values × 2 Replications = 8 Observations")
    print("=" * 70)

def main():
    """Main execution function."""
    print("\n" + "=" * 70)
    print("SYNTHETIC PSYCHOACOUSTIC DATA GENERATOR - STAGE 2 ISI DESIGN")
    print("=" * 70)
    print("Factorial Design: Frequency (2 levels) × ISI (2 levels)")
    print("Pure Sine Wave Tones - JND Estimation")
    print("=" * 70)
    
    # Set random seed for reproducibility
    np.random.seed(42)
    
    # Generate synthetic dataset
    print("\nGenerating synthetic data...")
    df = generate_synthetic_dataset()
    
    # Print design matrix
    print_design_matrix(df)
    
    # Save to CSV
    save_synthetic_data(df)
    
    # Print summary statistics
    print_summary_statistics(df)
    
    # Show first few records
    print("\n" + "=" * 70)
    print("FIRST FEW RECORDS:")
    print("=" * 70)
    print(df[['block_number', 'frequency_hz', 'isi_ms', 'replication', 
              'threshold_db', 'total_trials', 'usable_reversals']].to_string(index=False))
    
    return df

if __name__ == "__main__":
    df = main()
