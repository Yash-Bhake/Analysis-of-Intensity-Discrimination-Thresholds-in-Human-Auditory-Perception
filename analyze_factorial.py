"""
Stage 2 Factorial Design Analysis
Complete analysis pipeline for 2×2 factorial experiment
Includes: ANOVA, regression, effect plots, model adequacy checks
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from statsmodels.formula.api import ols
from statsmodels.stats.anova import anova_lm
import warnings
warnings.filterwarnings('ignore')

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 10

class FactorialAnalysis:
    def __init__(self, csv_file):
        """Initialize with data from Google Sheets export"""
        self.df = pd.read_csv(csv_file)
        self.prepare_data()
        
    def prepare_data(self):
        """Prepare and clean data"""
        # Rename columns for easier access
        self.df.columns = self.df.columns.str.strip().str.replace(' ', '_').str.replace('(', '').str.replace(')', '')
        
        # Create coded variables (-1, +1)
        self.df['Freq_Coded'] = self.df['Frequency_Hz'].map({250: -1, 1000: 1})
        self.df['Tone_Coded'] = self.df['Tone_Type'].map({'sine': -1, 'triangle': 1})
        
        # Create treatment labels
        self.df['Treatment'] = self.df['Frequency_Hz'].astype(str) + 'Hz_' + self.df['Tone_Type']
        
        print("Data loaded successfully!")
        print(f"Total observations: {len(self.df)}")
        print(f"Participants: {self.df['Participant_ID'].nunique()}")
        print(f"\nTreatment combinations:")
        print(self.df.groupby(['Frequency_Hz', 'Tone_Type']).size())
        
    def descriptive_statistics(self):
        """Calculate and display descriptive statistics"""
        print("\n" + "="*70)
        print("DESCRIPTIVE STATISTICS")
        print("="*70)
        
        # Overall statistics
        print("\nOverall Threshold Statistics:")
        print(f"Mean: {self.df['Threshold_dB'].mean():.3f} dB")
        print(f"Std Dev: {self.df['Threshold_dB'].std():.3f} dB")
        print(f"Min: {self.df['Threshold_dB'].min():.3f} dB")
        print(f"Max: {self.df['Threshold_dB'].max():.3f} dB")
        
        # By treatment
        print("\n\nMean Response by Treatment Combination:")
        treatment_means = self.df.groupby(['Frequency_Hz', 'Tone_Type'])['Threshold_dB'].agg([
            ('N', 'count'),
            ('Mean', 'mean'),
            ('Std', 'std'),
            ('Min', 'min'),
            ('Max', 'max')
        ]).round(3)
        print(treatment_means)
        
        # Estimate of experimental error
        print("\n\nExperimental Error Estimate:")
        # Within-treatment variance (pooled)
        within_var = self.df.groupby(['Frequency_Hz', 'Tone_Type'])['Threshold_dB'].var().mean()
        print(f"Pooled variance: {within_var:.4f}")
        print(f"Standard deviation: {np.sqrt(within_var):.4f} dB")
        
        return treatment_means
    
    def calculate_effects(self):
        """Calculate main and interaction effects with confidence intervals"""
        print("\n" + "="*70)
        print("MAIN AND INTERACTION EFFECTS")
        print("="*70)
        
        # Calculate means for each level
        freq_250_mean = self.df[self.df['Frequency_Hz'] == 250]['Threshold_dB'].mean()
        freq_1000_mean = self.df[self.df['Frequency_Hz'] == 1000]['Threshold_dB'].mean()
        
        sine_mean = self.df[self.df['Tone_Type'] == 'sine']['Threshold_dB'].mean()
        triangle_mean = self.df[self.df['Tone_Type'] == 'triangle']['Threshold_dB'].mean()
        
        # Main effects (difference between high and low levels)
        freq_effect = freq_1000_mean - freq_250_mean
        tone_effect = triangle_mean - sine_mean
        
        # Interaction effect
        # Calculate cell means
        mean_250_sine = self.df[(self.df['Frequency_Hz'] == 250) & (self.df['Tone_Type'] == 'sine')]['Threshold_dB'].mean()
        mean_250_tri = self.df[(self.df['Frequency_Hz'] == 250) & (self.df['Tone_Type'] == 'triangle')]['Threshold_dB'].mean()
        mean_1000_sine = self.df[(self.df['Frequency_Hz'] == 1000) & (self.df['Tone_Type'] == 'sine')]['Threshold_dB'].mean()
        mean_1000_tri = self.df[(self.df['Frequency_Hz'] == 1000) & (self.df['Tone_Type'] == 'triangle')]['Threshold_dB'].mean()
        
        interaction_effect = ((mean_1000_tri - mean_1000_sine) - (mean_250_tri - mean_250_sine)) / 2
        
        # Calculate standard errors and confidence intervals
        n_total = len(self.df)
        mse = self.df.groupby(['Frequency_Hz', 'Tone_Type'])['Threshold_dB'].var().mean()
        se_effect = np.sqrt(4 * mse / n_total)  # Standard error for effects
        
        # 95% CI (t-distribution, df = n - number of treatments)
        df = n_total - 4
        t_crit = stats.t.ppf(0.975, df)
        ci_half_width = t_crit * se_effect
        
        print(f"\nMain Effect of Frequency:")
        print(f"  Effect: {freq_effect:.3f} dB")
        print(f"  95% CI: [{freq_effect - ci_half_width:.3f}, {freq_effect + ci_half_width:.3f}]")
        print(f"  (1000 Hz mean: {freq_1000_mean:.3f}, 250 Hz mean: {freq_250_mean:.3f})")
        
        print(f"\nMain Effect of Tone Type:")
        print(f"  Effect: {tone_effect:.3f} dB")
        print(f"  95% CI: [{tone_effect - ci_half_width:.3f}, {tone_effect + ci_half_width:.3f}]")
        print(f"  (Triangle mean: {triangle_mean:.3f}, Sine mean: {sine_mean:.3f})")
        
        print(f"\nInteraction Effect (Frequency × Tone Type):")
        print(f"  Effect: {interaction_effect:.3f} dB")
        print(f"  95% CI: [{interaction_effect - ci_half_width:.3f}, {interaction_effect + ci_half_width:.3f}]")
        
        # Physical interpretation
        print("\n\nPhysical Interpretation:")
        if abs(freq_effect) > ci_half_width:
            print(f"• Frequency effect is significant: {abs(freq_effect):.3f} dB difference")
            print(f"  {'Higher' if freq_effect > 0 else 'Lower'} thresholds at 1000 Hz vs 250 Hz")
        else:
            print("• Frequency effect is not statistically significant")
        
        if abs(tone_effect) > ci_half_width:
            print(f"• Tone type effect is significant: {abs(tone_effect):.3f} dB difference")
            print(f"  {'Higher' if tone_effect > 0 else 'Lower'} thresholds for triangle vs sine waves")
        else:
            print("• Tone type effect is not statistically significant")
        
        if abs(interaction_effect) > ci_half_width:
            print(f"• Interaction is significant: Effect of tone type depends on frequency")
        else:
            print("• No significant interaction: Effects are additive")
        
        return {
            'freq_effect': freq_effect,
            'tone_effect': tone_effect,
            'interaction': interaction_effect,
            'ci_width': ci_half_width
        }
    
    def perform_anova(self, alpha=0.05):
        """Perform factorial ANOVA"""
        print("\n" + "="*70)
        print("ANALYSIS OF VARIANCE (ANOVA)")
        print("="*70)
        
        # Fit model
        model = ols('Threshold_dB ~ C(Frequency_Hz) + C(Tone_Type) + C(Frequency_Hz):C(Tone_Type)', 
                    data=self.df).fit()
        
        # ANOVA table
        anova_table = anova_lm(model, typ=2)
        
        print(f"\nSignificance level (α): {alpha}")
        print("\nANOVA Table:")
        print(anova_table.to_string())
        
        # Interpret results
        print("\n\nInterpretation:")
        for factor in anova_table.index[:-1]:  # Exclude residual
            p_value = anova_table.loc[factor, 'PR(>F)']
            if p_value < alpha:
                print(f"• {factor}: SIGNIFICANT (p = {p_value:.4f} < {alpha})")
            else:
                print(f"• {factor}: NOT significant (p = {p_value:.4f} ≥ {alpha})")
        
        return anova_table, model
    
    def regression_model(self):
        """Develop regression model in coded variables"""
        print("\n" + "="*70)
        print("REGRESSION MODEL (Coded Variables)")
        print("="*70)
        
        # Fit model with coded variables
        model_coded = ols('Threshold_dB ~ Freq_Coded * Tone_Coded', data=self.df).fit()
        
        print("\nModel Summary:")
        print(model_coded.summary())
        
        # Extract coefficients
        b0 = model_coded.params['Intercept']
        b1 = model_coded.params['Freq_Coded']
        b2 = model_coded.params['Tone_Coded']
        b12 = model_coded.params['Freq_Coded:Tone_Coded']
        
        print("\n\nRegression Equation (Coded Variables):")
        print(f"ŷ = {b0:.3f} + {b1:.3f}×X₁ + {b2:.3f}×X₂ + {b12:.3f}×X₁X₂")
        print("\nWhere:")
        print("  X₁ = Frequency coded (-1 = 250 Hz, +1 = 1000 Hz)")
        print("  X₂ = Tone Type coded (-1 = sine, +1 = triangle)")
        
        # Interpretation
        print("\n\nCoefficient Interpretation:")
        print(f"• b₀ (Intercept): {b0:.3f} dB - Grand mean of all observations")
        print(f"• b₁ (Frequency): {b1:.3f} dB - Half the frequency main effect")
        print(f"• b₂ (Tone Type): {b2:.3f} dB - Half the tone type main effect")
        print(f"• b₁₂ (Interaction): {b12:.3f} dB - Quarter of the interaction effect")
        
        # Convert to actual units (optional)
        print("\n\nRegression Equation (Actual Units):")
        print("For predictions, convert actual values to coded:")
        print("  X₁ = (Frequency - 625) / 375")
        print("  X₂ = 1 if triangle, -1 if sine")
        
        self.regression_model_coded = model_coded
        return model_coded
    
    def model_adequacy(self):
        """Check model adequacy assumptions"""
        print("\n" + "="*70)
        print("MODEL ADEQUACY CHECKING")
        print("="*70)
        
        model = self.regression_model_coded
        residuals = model.resid
        fitted = model.fittedvalues
        
        # R² and Adjusted R²
        print(f"\nR² = {model.rsquared:.4f}")
        print(f"Adjusted R² = {model.rsquared_adj:.4f}")
        print(f"Model explains {model.rsquared*100:.1f}% of variance in threshold")
        
        # Normality test
        _, p_norm = stats.shapiro(residuals)
        print(f"\n\nNormality Test (Shapiro-Wilk):")
        print(f"p-value = {p_norm:.4f}")
        if p_norm > 0.05:
            print("✓ Residuals appear normally distributed (p > 0.05)")
        else:
            print("⚠ Residuals may not be normally distributed (p ≤ 0.05)")
        
        # Constant variance (Levene's test on groups)
        groups = [self.df[self.df['Treatment'] == t]['Threshold_dB'].values 
                  for t in self.df['Treatment'].unique()]
        _, p_var = stats.levene(*groups)
        print(f"\n\nConstant Variance Test (Levene's):")
        print(f"p-value = {p_var:.4f}")
        if p_var > 0.05:
            print("✓ Variances appear homogeneous (p > 0.05)")
        else:
            print("⚠ Variances may not be homogeneous (p ≤ 0.05)")
        
        # Independence (Durbin-Watson)
        from statsmodels.stats.stattools import durbin_watson
        dw = durbin_watson(residuals)
        print(f"\n\nIndependence Test (Durbin-Watson):")
        print(f"DW statistic = {dw:.3f}")
        if 1.5 < dw < 2.5:
            print("✓ No evidence of autocorrelation (1.5 < DW < 2.5)")
        else:
            print("⚠ Possible autocorrelation")
        
        return {
            'residuals': residuals,
            'fitted': fitted,
            'r_squared': model.rsquared,
            'adj_r_squared': model.rsquared_adj
        }
    
    def create_plots(self, save_path='factorial_analysis_plots.png'):
        """Create all required plots"""
        fig = plt.figure(figsize=(16, 12))
        
        # 1. Main Effect Plots
        ax1 = plt.subplot(3, 3, 1)
        freq_means = self.df.groupby('Frequency_Hz')['Threshold_dB'].mean()
        ax1.plot([250, 1000], freq_means.values, 'o-', linewidth=2, markersize=10, color='#3b82f6')
        ax1.set_xlabel('Frequency (Hz)', fontsize=11, fontweight='bold')
        ax1.set_ylabel('Mean Threshold (dB)', fontsize=11, fontweight='bold')
        ax1.set_title('Main Effect: Frequency', fontsize=12, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        
        ax2 = plt.subplot(3, 3, 2)
        tone_means = self.df.groupby('Tone_Type')['Threshold_dB'].mean()
        ax2.plot([0, 1], tone_means.values, 'o-', linewidth=2, markersize=10, color='#8b5cf6')
        ax2.set_xticks([0, 1])
        ax2.set_xticklabels(['Sine', 'Triangle'])
        ax2.set_xlabel('Tone Type', fontsize=11, fontweight='bold')
        ax2.set_ylabel('Mean Threshold (dB)', fontsize=11, fontweight='bold')
        ax2.set_title('Main Effect: Tone Type', fontsize=12, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        
        # 2. Interaction Plot
        ax3 = plt.subplot(3, 3, 3)
        for tone in ['sine', 'triangle']:
            data = self.df[self.df['Tone_Type'] == tone]
            means = data.groupby('Frequency_Hz')['Threshold_dB'].mean()
            ax3.plot([250, 1000], means.values, 'o-', linewidth=2, 
                    markersize=10, label=tone.capitalize())
        ax3.set_xlabel('Frequency (Hz)', fontsize=11, fontweight='bold')
        ax3.set_ylabel('Mean Threshold (dB)', fontsize=11, fontweight='bold')
        ax3.set_title('Interaction Plot', fontsize=12, fontweight='bold')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # 3. Box plots by treatment
        ax4 = plt.subplot(3, 3, 4)
        self.df.boxplot(column='Threshold_dB', by='Treatment', ax=ax4)
        ax4.set_xlabel('Treatment Combination', fontsize=11, fontweight='bold')
        ax4.set_ylabel('Threshold (dB)', fontsize=11, fontweight='bold')
        ax4.set_title('Threshold Distribution by Treatment', fontsize=12, fontweight='bold')
        plt.sca(ax4)
        plt.xticks(rotation=45, ha='right')
        
        # 4. Residual vs Fitted
        adequacy = self.model_adequacy()
        ax5 = plt.subplot(3, 3, 5)
        ax5.scatter(adequacy['fitted'], adequacy['residuals'], alpha=0.6, s=50)
        ax5.axhline(y=0, color='r', linestyle='--', linewidth=2)
        ax5.set_xlabel('Fitted Values', fontsize=11, fontweight='bold')
        ax5.set_ylabel('Residuals', fontsize=11, fontweight='bold')
        ax5.set_title('Residuals vs Fitted Values', fontsize=12, fontweight='bold')
        ax5.grid(True, alpha=0.3)
        
        # 5. Normal Q-Q plot
        ax6 = plt.subplot(3, 3, 6)
        stats.probplot(adequacy['residuals'], dist="norm", plot=ax6)
        ax6.set_title('Normal Q-Q Plot', fontsize=12, fontweight='bold')
        ax6.grid(True, alpha=0.3)
        
        # 6. Histogram of residuals
        ax7 = plt.subplot(3, 3, 7)
        ax7.hist(adequacy['residuals'], bins=15, edgecolor='black', alpha=0.7)
        ax7.set_xlabel('Residuals', fontsize=11, fontweight='bold')
        ax7.set_ylabel('Frequency', fontsize=11, fontweight='bold')
        ax7.set_title('Distribution of Residuals', fontsize=12, fontweight='bold')
        ax7.grid(True, alpha=0.3)
        
        # 7. Means with error bars
        ax8 = plt.subplot(3, 3, 8)
        treatment_stats = self.df.groupby('Treatment')['Threshold_dB'].agg(['mean', 'std', 'count'])
        treatment_stats['se'] = treatment_stats['std'] / np.sqrt(treatment_stats['count'])
        
        x_pos = np.arange(len(treatment_stats))
        ax8.bar(x_pos, treatment_stats['mean'], yerr=treatment_stats['se'], 
               capsize=5, alpha=0.7, color='#3b82f6')
        ax8.set_xticks(x_pos)
        ax8.set_xticklabels(treatment_stats.index, rotation=45, ha='right')
        ax8.set_ylabel('Mean Threshold (dB)', fontsize=11, fontweight='bold')
        ax8.set_title('Treatment Means ± SE', fontsize=12, fontweight='bold')
        ax8.grid(True, alpha=0.3, axis='y')
        
        # 8. Scatter plot of actual vs predicted
        ax9 = plt.subplot(3, 3, 9)
        predicted = self.regression_model_coded.fittedvalues
        ax9.scatter(self.df['Threshold_dB'], predicted, alpha=0.6, s=50)
        min_val = min(self.df['Threshold_dB'].min(), predicted.min())
        max_val = max(self.df['Threshold_dB'].max(), predicted.max())
        ax9.plot([min_val, max_val], [min_val, max_val], 'r--', linewidth=2)
        ax9.set_xlabel('Actual Threshold (dB)', fontsize=11, fontweight='bold')
        ax9.set_ylabel('Predicted Threshold (dB)', fontsize=11, fontweight='bold')
        ax9.set_title('Actual vs Predicted', fontsize=12, fontweight='bold')
        ax9.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"\n✓ Plots saved as '{save_path}'")
        plt.show()
    
    def generate_report_summary(self, output_file='analysis_summary.txt'):
        """Generate text summary for report"""
        with open(output_file, 'w') as f:
            f.write("STAGE 2 FACTORIAL ANALYSIS SUMMARY\n")
            f.write("="*70 + "\n\n")
            
            f.write("DESIGN:\n")
            f.write(f"• 2×2 Full Factorial Design\n")
            f.write(f"• Factor A: Frequency (250 Hz, 1000 Hz)\n")
            f.write(f"• Factor B: Tone Type (Sine, Triangle)\n")
            f.write(f"• Replications: 2 per participant\n")
            f.write(f"• Total participants: {self.df['Participant_ID'].nunique()}\n")
            f.write(f"• Total observations: {len(self.df)}\n\n")
            
            # Add more sections...
            
        print(f"\n✓ Analysis summary saved as '{output_file}'")

def main():
    """Main analysis pipeline"""
    print("\n" + "="*70)
    print("STAGE 2 FACTORIAL DESIGN ANALYSIS")
    print("="*70)
    
    # Load data
    csv_file = input("\nEnter path to CSV file (exported from Google Sheets): ")
    analysis = FactorialAnalysis(csv_file)
    
    # Run all analyses
    print("\n\nRunning complete analysis pipeline...\n")
    
    treatment_means = analysis.descriptive_statistics()
    effects = analysis.calculate_effects()
    anova_table, anova_model = analysis.perform_anova()
    regression_model = analysis.regression_model()
    adequacy = analysis.model_adequacy()
    
    # Create plots
    analysis.create_plots()
    
    # Generate summary
    analysis.generate_report_summary()
    
    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)
    print("\nFiles generated:")
    print("  • factorial_analysis_plots.png")
    print("  • analysis_summary.txt")
    print("\nUse these results for your Stage 2 report!")

if __name__ == "__main__":
    main()
