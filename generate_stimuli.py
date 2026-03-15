"""
Psychoacoustic Stimulus Generator - Stage 2 Full Factorial Design
Generates stimuli for 2x2 factorial experiment:
- Factor A: Frequency (250 Hz, 1000 Hz)
- Factor B: Tone Type (Sine wave, Triangle wave)
"""

import numpy as np
from pydub import AudioSegment
from pathlib import Path

# Experimental parameters - Full Factorial Design
FREQUENCIES = [250, 1000]  # Hz - Factor A (2 levels)
TONE_TYPES = ['sine', 'triangle']  # Factor B (2 levels)
DURATION = 750  # ms - Fixed at 0.75 seconds
PEDESTAL_INTENSITY = -15  # dBFS - Fixed moderate level
SAMPLE_RATE = 44100  # Hz
RAMP_DURATION = 50  # ms for cosine-squared ramps
BITRATE = 128  # kbps - Fixed

# Delta I range for adaptive staircase
DELTA_I_RANGE = np.arange(0.5, 12.5, 0.5)  # 0.5 to 12 dB in 0.5 dB steps


def apply_cosine_ramp(signal: np.ndarray, ramp_samples: int) -> np.ndarray:
    """Apply cosine-squared onset and offset ramps to prevent clicks."""
    ramp = np.sin(np.linspace(0, np.pi / 2, ramp_samples)) ** 2
    signal[:ramp_samples] *= ramp
    signal[-ramp_samples:] *= ramp[::-1]
    return signal


def generate_sine_wave(frequency: float, duration_ms: float, intensity_dbfs: float) -> np.ndarray:
    """Generate a pure sine wave tone."""
    n_samples = int((duration_ms / 1000.0) * SAMPLE_RATE)
    t = np.linspace(0, duration_ms / 1000.0, n_samples, endpoint=False)
    
    # Generate sine wave
    signal = np.sin(2 * np.pi * frequency * t)
    
    # Apply ramps
    ramp_samples = int((RAMP_DURATION / 1000.0) * SAMPLE_RATE)
    signal = apply_cosine_ramp(signal, ramp_samples)
    
    # Apply intensity
    amplitude = 10 ** (intensity_dbfs / 20.0)
    signal *= amplitude
    
    return signal


def generate_triangle_wave(frequency: float, duration_ms: float, intensity_dbfs: float) -> np.ndarray:
    """Generate a triangle wave tone."""
    n_samples = int((duration_ms / 1000.0) * SAMPLE_RATE)
    t = np.linspace(0, duration_ms / 1000.0, n_samples, endpoint=False)
    
    # Generate triangle wave using Fourier series (first 20 harmonics for smoothness)
    signal = np.zeros(n_samples)
    for k in range(1, 21):  # Use 20 harmonics
        harmonic = ((-1) ** k) / ((2*k - 1) ** 2)
        signal += harmonic * np.sin(2 * np.pi * (2*k - 1) * frequency * t)
    
    signal *= (8 / (np.pi ** 2))  # Normalize triangle wave
    
    # Apply ramps
    ramp_samples = int((RAMP_DURATION / 1000.0) * SAMPLE_RATE)
    signal = apply_cosine_ramp(signal, ramp_samples)
    
    # Apply intensity
    amplitude = 10 ** (intensity_dbfs / 20.0)
    signal *= amplitude
    
    return signal


def save_as_mp3(signal: np.ndarray, filename: str) -> None:
    """Save numpy array as MP3 file using pydub."""
    # Convert to 16-bit PCM
    signal_int16 = (signal * 32767).astype(np.int16)
    
    # Create AudioSegment
    audio_segment = AudioSegment(
        signal_int16.tobytes(),
        frame_rate=SAMPLE_RATE,
        sample_width=2,
        channels=1
    )
    
    # Export as MP3
    audio_segment.export(filename, format="mp3", bitrate=f"{BITRATE}k")


def generate_stimulus_library(output_dir: str = "stimuli") -> None:
    """Generate complete stimulus library for 2x2 factorial experiment."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    total_files = 0
    
    print("=" * 70)
    print("PSYCHOACOUSTIC STIMULUS GENERATOR - STAGE 2 FACTORIAL DESIGN")
    print("=" * 70)
    print(f"\nFactorial Design: 2 × 2")
    print(f"Factor A (Frequency): {FREQUENCIES} Hz")
    print(f"Factor B (Tone Type): {TONE_TYPES}")
    print(f"Fixed Parameters:")
    print(f"  - Duration: {DURATION} ms")
    print(f"  - Pedestal Intensity: {PEDESTAL_INTENSITY} dBFS")
    print(f"  - Bitrate: {BITRATE} kbps")
    print(f"  - Sample Rate: {SAMPLE_RATE} Hz")
    print("\n" + "=" * 70)
    
    # Loop through all factor combinations
    for freq in FREQUENCIES:
        for tone_type in TONE_TYPES:
            
            print(f"\nGenerating: {freq} Hz {tone_type} wave")
            
            # Select tone generation function
            if tone_type == 'sine':
                generate_func = generate_sine_wave
            else:  # triangle
                generate_func = generate_triangle_wave
            
            # Generate Standard tone (I)
            standard_filename = f"{output_dir}/freq{freq}_{tone_type}_delta0.0.mp3"
            standard_signal = generate_func(freq, DURATION, PEDESTAL_INTENSITY)
            save_as_mp3(standard_signal, standard_filename)
            total_files += 1
            
            # Generate Comparison tones (I + ΔI)
            for delta_i in DELTA_I_RANGE:
                comparison_intensity = PEDESTAL_INTENSITY + delta_i
                
                # Ensure we don't exceed 0 dBFS
                if comparison_intensity > 0:
                    comparison_intensity = 0.0
                
                comparison_filename = f"{output_dir}/freq{freq}_{tone_type}_delta{delta_i:.1f}.mp3"
                comparison_signal = generate_func(freq, DURATION, comparison_intensity)
                save_as_mp3(comparison_signal, comparison_filename)
                total_files += 1
            
            print(f"  ✓ Generated {len(DELTA_I_RANGE) + 1} files")
    
    print("\n" + "=" * 70)
    print(f"✓ COMPLETE! Generated {total_files} stimulus files")
    print(f"✓ Output directory: {output_dir}/")
    print(f"\nFile naming convention:")
    print(f"  freqXXX_tonetype_deltaX.X.mp3")
    print(f"  Example: freq1000_sine_delta3.5.mp3")
    print("=" * 70)


def generate_calibration_tone(output_dir: str = "stimuli") -> None:
    """Generate a 1000 Hz sine wave calibration tone for volume adjustment."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    calibration_signal = generate_sine_wave(
        frequency=1000,
        duration_ms=1000,
        intensity_dbfs=-15
    )
    
    calibration_filename = f"{output_dir}/calibration_tone.mp3"
    save_as_mp3(calibration_signal, calibration_filename)
    
    print(f"\n✓ Calibration tone generated: {calibration_filename}")


if __name__ == "__main__":
    print("\n")
    generate_stimulus_library()
    generate_calibration_tone()
    
    print("\n" + "=" * 70)
    print("SETUP INSTRUCTIONS:")
    print("=" * 70)
    print("1. Install required packages:")
    print("   pip install numpy pydub")
    print("2. Install ffmpeg (required by pydub):")
    print("   - Ubuntu/Debian: sudo apt-get install ffmpeg")
    print("   - macOS: brew install ffmpeg")
    print("   - Windows: Download from https://ffmpeg.org/download.html")
    print("3. Run this script: python generate_stimuli.py")
    print("4. Upload the 'stimuli' folder to your web hosting")
    print("=" * 70)
    print("\nTotal treatment combinations: 4 (2 frequencies × 2 tone types)")
    print("Replications per participant: 2")
    print("Total blocks per participant: 8")
    print("Trials per block: ~25-40 (adaptive termination)")
    print("=" * 70)