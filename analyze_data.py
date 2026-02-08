"""
Example Data Analysis Script for Psychoacoustic Experiment
Analyzes intensity discrimination thresholds from Google Sheets export
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

# Set visualization style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)

def load_data(csv_file):
    """Load data from Google Sheets CSV export"""
    df = pd.read_csv(csv_file)
    
    # Convert timestamp to datetime
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    
    # Rename columns for easier access
    df.columns = df.columns.str.strip().str.replace(' ', '_').str.replace('(', '').str.replace(')', '')
    
    return df

def descriptive_statistics(df):
    """Calculate descriptive statistics"""
    print("=" * 60)
    print("DESCRIPTIVE STATISTICS")
    print("=" * 60)
    
    print(f"\nTotal Participants: {len(df)}")
    print(f"Mean Age: {df['Age'].mean():.1f} (SD = {df['Age'].std():.1f})")
    print(f"\nGender Distribution:")
    print(df['Gender'].value_counts())
    print(f"\nMusical Background:")
    print(df['Musical_Background'].value_counts())
    
    print(f"\n\nOVERALL THRESHOLD STATISTICS:")
    print(f"Mean Threshold: {df['Calculated_Threshold_dB'].mean():.3f} dB")
    print(f"Median Threshold: {df['Calculated_Threshold_dB'].median():.3f} dB")
    print(f"SD: {df['Calculated_Threshold_dB'].std():.3f} dB")
    print(f"Range: {df['Calculated_Threshold_dB'].min():.3f} - {df['Calculated_Threshold_dB'].max():.3f} dB")

def threshold_by_frequency(df):
    """Analyze thresholds by frequency"""
    print("\n" + "=" * 60)
    print("THRESHOLD BY FREQUENCY")
    print("=" * 60)
    
    freq_stats = df.groupby('Frequency_Hz')['Calculated_Threshold_dB'].agg([
        ('N', 'count'),
        ('Mean', 'mean'),
        ('SD', 'std'),
        ('Median', 'median'),
        ('Min', 'min'),
        ('Max', 'max')
    ]).round(3)
    
    print("\n", freq_stats)
    
    # Statistical test (one-way ANOVA)
    frequencies = df['Frequency_Hz'].unique()
    groups = [df[df['Frequency_Hz'] == freq]['Calculated_Threshold_dB'].values 
              for freq in frequencies]
    
    f_stat, p_value = stats.f_oneway(*groups)
    print(f"\nOne-way ANOVA:")
    print(f"F-statistic: {f_stat:.3f}")
    print(f"p-value: {p_value:.4f}")
    
    if p_value < 0.05:
        print("Significant difference between frequencies (p < 0.05)")
    else:
        print("No significant difference between frequencies (p ≥ 0.05)")
    
    return freq_stats

def threshold_by_pedestal(df):
    """Analyze thresholds by pedestal intensity"""
    print("\n" + "=" * 60)
    print("THRESHOLD BY PEDESTAL INTENSITY")
    print("=" * 60)
    
    ped_stats = df.groupby('Pedestal_dBFS')['Calculated_Threshold_dB'].agg([
        ('N', 'count'),
        ('Mean', 'mean'),
        ('SD', 'std'),
        ('Median', 'median')
    ]).round(3)
    
    print("\n", ped_stats)
    
    # Test for Weber's Law (threshold proportional to pedestal)
    # Convert pedestal to linear amplitude
    df['Pedestal_Linear'] = 10 ** (df['Pedestal_dBFS'] / 20)
    
    correlation = df[['Pedestal_Linear', 'Calculated_Threshold_dB']].corr().iloc[0, 1]
    print(f"\nCorrelation (Pedestal vs Threshold): {correlation:.3f}")
    
    return ped_stats

def plot_results(df):
    """Create visualization plots"""
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    
    # 1. Threshold by Frequency
    ax1 = axes[0, 0]
    freq_data = df.groupby('Frequency_Hz')['Calculated_Threshold_dB'].apply(list)
    positions = list(freq_data.index)
    ax1.violinplot(freq_data.values, positions=positions, widths=100, 
                   showmeans=True, showmedians=True)
    ax1.set_xlabel('Frequency (Hz)', fontsize=12)
    ax1.set_ylabel('Threshold (dB)', fontsize=12)
    ax1.set_title('Intensity Discrimination Threshold by Frequency', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    
    # 2. Threshold by Pedestal
    ax2 = axes[0, 1]
    sns.boxplot(data=df, x='Pedestal_dBFS', y='Calculated_Threshold_dB', ax=ax2)
    ax2.set_xlabel('Pedestal Intensity (dBFS)', fontsize=12)
    ax2.set_ylabel('Threshold (dB)', fontsize=12)
    ax2.set_title('Threshold by Pedestal Intensity', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    
    # 3. Distribution of Thresholds
    ax3 = axes[1, 0]
    ax3.hist(df['Calculated_Threshold_dB'], bins=20, edgecolor='black', alpha=0.7)
    ax3.axvline(df['Calculated_Threshold_dB'].mean(), color='red', 
                linestyle='--', linewidth=2, label=f'Mean = {df["Calculated_Threshold_dB"].mean():.2f} dB')
    ax3.axvline(df['Calculated_Threshold_dB'].median(), color='blue', 
                linestyle='--', linewidth=2, label=f'Median = {df["Calculated_Threshold_dB"].median():.2f} dB')
    ax3.set_xlabel('Threshold (dB)', fontsize=12)
    ax3.set_ylabel('Frequency Count', fontsize=12)
    ax3.set_title('Distribution of Intensity Discrimination Thresholds', fontsize=14, fontweight='bold')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 4. Threshold by Musical Background
    ax4 = axes[1, 1]
    musical_order = ['none', 'some', 'moderate', 'extensive', 'professional']
    df_music = df[df['Musical_Background'].isin(musical_order)]
    sns.violinplot(data=df_music, x='Musical_Background', y='Calculated_Threshold_dB', 
                   order=musical_order, ax=ax4)
    ax4.set_xlabel('Musical Background', fontsize=12)
    ax4.set_ylabel('Threshold (dB)', fontsize=12)
    ax4.set_title('Threshold by Musical Training', fontsize=14, fontweight='bold')
    ax4.tick_params(axis='x', rotation=45)
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('threshold_analysis.png', dpi=300, bbox_inches='tight')
    print("\n✓ Plots saved as 'threshold_analysis.png'")
    plt.show()

def analyze_individual_trials(df, subject_id):
    """Analyze individual participant's trial-by-trial data"""
    subject_data = df[df['Subject_ID'] == subject_id]
    
    if len(subject_data) == 0:
        print(f"Subject {subject_id} not found!")
        return
    
    import json
    trial_data = json.loads(subject_data['Raw_Trial_Data'].iloc[0])
    
    trials = [t['trialNumber'] for t in trial_data]
    delta_i = [t['deltaI'] for t in trial_data]
    correct = [1 if t['correct'] else 0 for t in trial_data]
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
    
    # Plot 1: ΔI over trials
    ax1.plot(trials, delta_i, marker='o', linewidth=2, markersize=4)
    ax1.set_xlabel('Trial Number', fontsize=12)
    ax1.set_ylabel('ΔI (dB)', fontsize=12)
    ax1.set_title(f'Staircase Progression - Subject {subject_id}', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    
    # Mark reversals
    reversals = []
    for i in range(1, len(delta_i)):
        if (delta_i[i] > delta_i[i-1] and delta_i[i-1] < delta_i[i-2] if i > 1 else False) or \
           (delta_i[i] < delta_i[i-1] and delta_i[i-1] > delta_i[i-2] if i > 1 else False):
            reversals.append(i)
            ax1.axvline(x=trials[i], color='red', linestyle='--', alpha=0.5)
    
    # Plot 2: Correct/Incorrect responses
    ax2.scatter(trials, correct, c=correct, cmap='RdYlGn', s=100, alpha=0.6)
    ax2.set_xlabel('Trial Number', fontsize=12)
    ax2.set_ylabel('Response', fontsize=12)
    ax2.set_yticks([0, 1])
    ax2.set_yticklabels(['Incorrect', 'Correct'])
    ax2.set_title('Response Accuracy', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f'subject_{subject_id}_trials.png', dpi=300, bbox_inches='tight')
    print(f"\n✓ Individual trial plot saved as 'subject_{subject_id}_trials.png'")
    plt.show()
    
    # Print summary
    print(f"\nSubject {subject_id} Summary:")
    print(f"Total Trials: {len(trials)}")
    print(f"Accuracy: {sum(correct)/len(correct)*100:.1f}%")
    print(f"Final Threshold: {subject_data['Calculated_Threshold_dB'].iloc[0]:.3f} dB")
    print(f"Frequency: {subject_data['Frequency_Hz'].iloc[0]} Hz")

def main():
    """Main analysis pipeline"""
    print("PSYCHOACOUSTIC INTENSITY DISCRIMINATION ANALYSIS")
    print("=" * 60)
    
    # Load data
    csv_file = input("Enter path to CSV file (exported from Google Sheets): ")
    df = load_data(csv_file)
    
    # Run analyses
    descriptive_statistics(df)
    freq_stats = threshold_by_frequency(df)
    ped_stats = threshold_by_pedestal(df)
    
    # Create plots
    plot_results(df)
    
    # Optional: Analyze individual participant
    analyze = input("\nAnalyze individual participant? (y/n): ")
    if analyze.lower() == 'y':
        subject_id = input("Enter Subject ID: ")
        analyze_individual_trials(df, subject_id)
    
    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()
