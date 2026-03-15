"""
Psychoacoustic Stimulus Generator
Generates a library of synthetic audio files for Intensity Discrimination experiments
using a 2AFC paradigm with adaptive staircase procedure.
"""

import numpy as np
import librosa
from pydub import AudioSegment
import os
from pathlib import Path
from typing import Tuple
import io

# Experimental parameters
FREQUENCIES = [250, 500, 1000, 2000, 3000]  # Hz
PEDESTAL_INTENSITIES = [-20, -15, -10, -5]  # dBFS
DURATIONS = [200, 500, 800, 1100, 1500]  # ms
BITRATES = [32, 64, 128, 256]  # kbps
DELTA_I_RANGE = np.arange(0.5, 12.5, 0.5)  # 0.5 to 12 dB in 0.5 dB steps
SAMPLE_RATE = 44100  # Hz
RAMP_DURATION = 50  # ms for cosine-squared ramps


def apply_cosine_ramp(signal: np.ndarray, ramp_samples: int) -> np.ndarray:
    """
    Apply cosine-squared onset and offset ramps to prevent clicks.
    
    Args:
        signal: Audio signal array
        ramp_samples: Number of samples for each ramp
    
    Returns:
        Ramped signal
    """
    ramp = np.sin(np.linspace(0, np.pi / 2, ramp_samples)) ** 2
    
    # Apply onset ramp
    signal[:ramp_samples] *= ramp
    
    # Apply offset ramp
    signal[-ramp_samples:] *= ramp[::-1]
    
    return signal


def generate_tone(frequency: float, duration_ms: float, 
                  intensity_dbfs: float) -> np.ndarray:
    """
    Generate a pure tone with specified parameters.
    
    Args:
        frequency: Tone frequency in Hz
        duration_ms: Duration in milliseconds
        intensity_dbfs: Intensity level in dBFS
    
    Returns:
        Audio signal array (normalized to [-1, 1])
    """
    # Calculate number of samples
    n_samples = int((duration_ms / 1000.0) * SAMPLE_RATE)
    ramp_samples = int((RAMP_DURATION / 1000.0) * SAMPLE_RATE)
    
    # Generate time array
    t = np.linspace(0, duration_ms / 1000.0, n_samples, endpoint=False)
    
    # Generate pure tone
    signal = np.sin(2 * np.pi * frequency * t)
    
    # Apply cosine-squared ramps
    signal = apply_cosine_ramp(signal, ramp_samples)
    
    # Convert dBFS to linear amplitude
    # dBFS: 0 dBFS = maximum amplitude (1.0)
    # Formula: amplitude = 10^(dBFS/20)
    amplitude = 10 ** (intensity_dbfs / 20.0)
    signal *= amplitude
    
    return signal


def save_as_mp3(signal: np.ndarray, filename: str, bitrate: int) -> None:
    """
    Save numpy array as MP3 file using pydub.
    
    Args:
        signal: Audio signal array
        filename: Output filename
        bitrate: MP3 bitrate in kbps
    """
    # Convert to 16-bit PCM
    signal_int16 = (signal * 32767).astype(np.int16)
    
    # Create AudioSegment from numpy array
    audio_segment = AudioSegment(
        signal_int16.tobytes(),
        frame_rate=SAMPLE_RATE,
        sample_width=2,  # 16-bit = 2 bytes
        channels=1  # Mono
    )
    
    # Export as MP3
    audio_segment.export(
        filename,
        format="mp3",
        bitrate=f"{bitrate}k"
    )


def generate_stimulus_library(output_dir: str = "stimuli") -> None:
    """
    Generate complete stimulus library for the experiment.
    
    Args:
        output_dir: Directory to save generated stimuli
    """
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    total_files = 0
    
    print("Generating Psychoacoustic Stimulus Library...")
    print("=" * 60)
    
    # Loop through all factor combinations
    for freq in FREQUENCIES:
        for pedestal in PEDESTAL_INTENSITIES:
            for duration in DURATIONS:
                for bitrate in BITRATES:
                    
                    # Generate Standard tone (I)
                    standard_filename = f"{output_dir}/freq{freq}_ped{pedestal}_dur{duration}_br{bitrate}_delta0.0.mp3"
                    standard_signal = generate_tone(freq, duration, pedestal)
                    save_as_mp3(standard_signal, standard_filename, bitrate)
                    total_files += 1
                    
                    # Generate Comparison tones (I + ΔI)
                    for delta_i in DELTA_I_RANGE:
                        comparison_intensity = pedestal + delta_i
                        
                        # Ensure we don't exceed 0 dBFS
                        if comparison_intensity > 0:
                            comparison_intensity = 0.0
                        
                        comparison_filename = f"{output_dir}/freq{freq}_ped{pedestal}_dur{duration}_br{bitrate}_delta{delta_i:.1f}.mp3"
                        comparison_signal = generate_tone(freq, duration, comparison_intensity)
                        save_as_mp3(comparison_signal, comparison_filename, bitrate)
                        total_files += 1
                    
                    # Progress indicator
                    if total_files % 100 == 0:
                        print(f"Generated {total_files} files...")
    
    print("=" * 60)
    print(f"✓ Complete! Generated {total_files} stimulus files")
    print(f"✓ Output directory: {output_dir}/")
    print(f"\nFile naming convention:")
    print(f"  freqXXXX_pedXX_durXXXX_brXXX_deltaX.X.mp3")
    print(f"\nParameters:")
    print(f"  Frequencies: {FREQUENCIES} Hz")
    print(f"  Pedestals: {PEDESTAL_INTENSITIES} dBFS")
    print(f"  Durations: {DURATIONS} ms")
    print(f"  Bitrates: {BITRATES} kbps")
    print(f"  Delta I: {DELTA_I_RANGE[0]:.1f} to {DELTA_I_RANGE[-1]:.1f} dB (0.5 dB steps)")


def generate_calibration_tone(output_dir: str = "stimuli") -> None:
    """
    Generate a 1000 Hz calibration tone for volume adjustment.
    
    Args:
        output_dir: Directory to save calibration tone
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    calibration_signal = generate_tone(
        frequency=1000,
        duration_ms=1000,
        intensity_dbfs=-15  # Comfortable level
    )
    
    calibration_filename = f"{output_dir}/calibration_tone.mp3"
    save_as_mp3(calibration_signal, calibration_filename, 128)
    
    print(f"✓ Calibration tone generated: {calibration_filename}")


if __name__ == "__main__":
    # Generate all stimuli
    generate_stimulus_library()
    
    # Generate calibration tone
    generate_calibration_tone()
    
    print("\n" + "=" * 60)
    print("SETUP INSTRUCTIONS:")
    print("=" * 60)
    print("1. Install required packages:")
    print("   pip install numpy librosa pydub")
    print("2. Install ffmpeg (required by pydub):")
    print("   - Ubuntu/Debian: sudo apt-get install ffmpeg")
    print("   - macOS: brew install ffmpeg")
    print("   - Windows: Download from https://ffmpeg.org/download.html")
    print("3. Run this script: python generate_stimuli.py")
    print("4. Upload the 'stimuli' folder to your web hosting service")
    print("=" * 60)
