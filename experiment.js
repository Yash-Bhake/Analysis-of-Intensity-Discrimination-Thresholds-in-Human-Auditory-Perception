/**
 * Psychoacoustic Experiment - Main JavaScript
 * 2AFC Intensity Discrimination with 3-down 1-up Staircase
 */

// Configuration
const CONFIG = {
    GOOGLE_SCRIPT_URL: 'https://script.google.com/macros/s/AKfycbwwYdWSiwyouO2etOI9xftWl-_js4lNQtRwYGjMb0-WE5Qc2vQW3o0Wqu2fjxBu2Cr_9A/exec', // Replace with your Google Apps Script URL
    STIMULI_PATH: 'stimuli/', // Path to stimuli folder
    DELTA_I_STEPS: Array.from({length: 24}, (_, i) => (i + 1) * 0.5), // 0.5 to 12.0 dB
    INITIAL_DELTA_I: 6.0, // Starting intensity difference
    MAX_TRIALS: 40,
    TARGET_REVERSALS: 8,
    ISI: 500, // Inter-stimulus interval in ms
    STEP_SIZE: 0.5, // dB step size
    CONSECUTIVE_CORRECT_NEEDED: 3 // For 3-down 1-up
};

// Experimental parameters
const FREQUENCIES = [250, 500, 1000, 2000, 3000];
const PEDESTAL_INTENSITIES = [-20, -15, -10, -5];
const DURATIONS = [200, 500, 800, 1100, 1500];
const BITRATES = [32, 64, 128, 256];

// Global state
let experimentState = {
    subjectID: null,
    demographics: {},
    condition: {},
    currentTrial: 0,
    deltaI: CONFIG.INITIAL_DELTA_I,
    reversals: [],
    correctStreak: 0,
    trialHistory: [],
    lastDirection: null, // 'up' or 'down'
    audioContext: null,
    calibrationPlayed: false
};

// Audio handling
class AudioPlayer {
    constructor() {
        this.context = new (window.AudioContext || window.webkitAudioContext)();
        this.currentSource = null;
    }

    async loadAudioFile(filename) {
        const response = await fetch(CONFIG.STIMULI_PATH + filename);
        const arrayBuffer = await response.arrayBuffer();
        return await this.context.decodeAudioData(arrayBuffer);
    }

    async playBuffer(audioBuffer, when = 0) {
        const source = this.context.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(this.context.destination);
        source.start(when);
        return source;
    }

    async playSequence(buffer1, buffer2, isi_ms) {
        const now = this.context.currentTime;
        const duration1 = buffer1.duration;
        const isi_sec = isi_ms / 1000;

        await this.playBuffer(buffer1, now);
        await this.playBuffer(buffer2, now + duration1 + isi_sec);

        return (duration1 + isi_sec + buffer2.duration) * 1000;
    }

    getContext() {
        return this.context;
    }
}

const audioPlayer = new AudioPlayer();

// Utility functions
function generateSubjectID() {
    return 'S' + Date.now().toString(36) + Math.random().toString(36).substr(2, 5);
}

function randomChoice(array) {
    return array[Math.floor(Math.random() * array.length)];
}

function roundToStep(value, step) {
    return Math.round(value / step) * step;
}

// UI Control Functions
function proceedFromConsent() {
    if (!document.getElementById('consent-checkbox').checked) {
        return;
    }
    showStage('stage-demographics');
}

function proceedFromDemographics() {
    const age = document.getElementById('age').value;
    const gender = document.getElementById('gender').value;
    const musicalBackground = document.getElementById('musical-background').value;
    const noiseLevel = document.getElementById('noise-level').value;

    if (!age || !gender || !musicalBackground || !noiseLevel) {
        alert('Please complete all fields before proceeding.');
        return;
    }

    experimentState.demographics = {
        age: parseInt(age),
        gender,
        musicalBackground,
        noiseLevel
    };

    showStage('stage-calibration');
}

async function playCalibrationTone() {
    const btn = document.getElementById('calibration-play-btn');
    btn.disabled = true;
    btn.textContent = 'Playing...';

    try {
        const buffer = await audioPlayer.loadAudioFile('calibration_tone.mp3');
        await audioPlayer.playBuffer(buffer);
        
        setTimeout(() => {
            btn.disabled = false;
            btn.textContent = 'Play Calibration Tone';
            experimentState.calibrationPlayed = true;
        }, buffer.duration * 1000 + 500);
    } catch (error) {
        console.error('Error playing calibration tone:', error);
        alert('Error loading calibration tone. Please ensure the stimuli folder is accessible.');
        btn.disabled = false;
        btn.textContent = 'Play Calibration Tone';
    }
}

function startExperiment() {
    if (!document.getElementById('calibration-checkbox').checked) {
        return;
    }

    // Generate subject ID
    experimentState.subjectID = generateSubjectID();

    // Randomly select experimental condition
    experimentState.condition = {
        frequency: randomChoice(FREQUENCIES),
        pedestal: randomChoice(PEDESTAL_INTENSITIES),
        duration: randomChoice(DURATIONS),
        bitrate: randomChoice(BITRATES)
    };

    // Update display
    document.getElementById('current-freq').textContent = experimentState.condition.frequency + ' Hz';

    // Initialize trial
    showStage('stage-experiment');
    setTimeout(runTrial, 1000);
}

// Staircase filename generator
function getStandardFilename() {
    const { frequency, pedestal, duration, bitrate } = experimentState.condition;
    return `freq${frequency}_ped${pedestal}_dur${duration}_br${bitrate}_delta0.0.mp3`;
}

function getComparisonFilename(deltaI) {
    const { frequency, pedestal, duration, bitrate } = experimentState.condition;
    const roundedDelta = deltaI.toFixed(1);
    return `freq${frequency}_ped${pedestal}_dur${duration}_br${bitrate}_delta${roundedDelta}.mp3`;
}

// Trial execution
async function runTrial() {
    experimentState.currentTrial++;
    
    // Update UI
    updateTrialDisplay();

    // Disable response buttons
    document.getElementById('response-buttons').style.display = 'none';

    // Load audio files
    const standardFile = getStandardFilename();
    const comparisonFile = getComparisonFilename(experimentState.deltaI);

    try {
        document.getElementById('playback-status').innerHTML = 'Loading sounds...';
        
        const standardBuffer = await audioPlayer.loadAudioFile(standardFile);
        const comparisonBuffer = await audioPlayer.loadAudioFile(comparisonFile);

        // Randomize which interval contains the comparison
        const comparisonFirst = Math.random() < 0.5;
        const buffer1 = comparisonFirst ? comparisonBuffer : standardBuffer;
        const buffer2 = comparisonFirst ? standardBuffer : comparisonBuffer;

        // Store the correct answer
        experimentState.currentCorrectAnswer = comparisonFirst ? 1 : 2;

        // Play Sound 1
        document.getElementById('playback-status').innerHTML = '🔊 Sound 1 Playing... <span class="sound-icon"></span>';
        document.getElementById('playback-status').className = 'playback-indicator playing';
        
        await audioPlayer.playBuffer(buffer1);
        await sleep(buffer1.duration * 1000);

        // Inter-stimulus interval
        document.getElementById('playback-status').textContent = 'Silence...';
        document.getElementById('playback-status').className = 'playback-indicator';
        await sleep(CONFIG.ISI);

        // Play Sound 2
        document.getElementById('playback-status').innerHTML = '🔊 Sound 2 Playing... <span class="sound-icon"></span>';
        document.getElementById('playback-status').className = 'playback-indicator playing';
        
        await audioPlayer.playBuffer(buffer2);
        await sleep(buffer2.duration * 1000);

        // Show response buttons
        document.getElementById('playback-status').textContent = 'Which sound was LOUDER?';
        document.getElementById('playback-status').className = 'playback-indicator';
        document.getElementById('response-buttons').style.display = 'flex';

    } catch (error) {
        console.error('Error during trial:', error);
        document.getElementById('playback-status').textContent = 'Error loading sounds. Please refresh the page.';
    }
}

function respondSound(choice) {
    const correct = (choice === experimentState.currentCorrectAnswer);
    
    // Record trial data
    const trialData = {
        trialNumber: experimentState.currentTrial,
        deltaI: experimentState.deltaI,
        response: choice,
        correctAnswer: experimentState.currentCorrectAnswer,
        correct: correct,
        timestamp: new Date().toISOString()
    };
    experimentState.trialHistory.push(trialData);

    // Update staircase
    updateStaircase(correct);

    // Check termination conditions
    if (experimentState.reversals.length >= CONFIG.TARGET_REVERSALS || 
        experimentState.currentTrial >= CONFIG.MAX_TRIALS) {
        completeExperiment();
    } else {
        setTimeout(runTrial, 800);
    }
}

// 3-down 1-up Staircase procedure
function updateStaircase(correct) {
    let newDeltaI = experimentState.deltaI;
    let direction = null;

    if (correct) {
        experimentState.correctStreak++;
        
        // 3 consecutive correct → decrease deltaI (make task harder)
        if (experimentState.correctStreak >= CONFIG.CONSECUTIVE_CORRECT_NEEDED) {
            newDeltaI = Math.max(CONFIG.DELTA_I_STEPS[0], experimentState.deltaI - CONFIG.STEP_SIZE);
            direction = 'down';
            experimentState.correctStreak = 0;
        }
    } else {
        // 1 incorrect → increase deltaI (make task easier)
        newDeltaI = Math.min(CONFIG.DELTA_I_STEPS[CONFIG.DELTA_I_STEPS.length - 1], 
                             experimentState.deltaI + CONFIG.STEP_SIZE);
        direction = 'up';
        experimentState.correctStreak = 0;
    }

    // Detect reversal
    if (direction && experimentState.lastDirection && direction !== experimentState.lastDirection) {
        experimentState.reversals.push({
            trial: experimentState.currentTrial,
            deltaI: experimentState.deltaI
        });
    }

    experimentState.lastDirection = direction;
    experimentState.deltaI = roundToStep(newDeltaI, CONFIG.STEP_SIZE);
}

function updateTrialDisplay() {
    document.getElementById('trial-number').textContent = 
        `${experimentState.currentTrial}/${CONFIG.MAX_TRIALS}`;
    document.getElementById('reversal-count').textContent = 
        `${experimentState.reversals.length}/${CONFIG.TARGET_REVERSALS}`;
    document.getElementById('current-delta').textContent = 
        `${experimentState.deltaI.toFixed(1)} dB`;
    
    const progress = (experimentState.currentTrial / CONFIG.MAX_TRIALS) * 100;
    document.getElementById('progress-fill').style.width = `${progress}%`;
}

// Experiment completion
function completeExperiment() {
    // Calculate threshold (mean of last 6 reversals)
    const lastReversals = experimentState.reversals.slice(-6);
    const threshold = lastReversals.length > 0 
        ? lastReversals.reduce((sum, r) => sum + r.deltaI, 0) / lastReversals.length
        : experimentState.deltaI;

    // Update completion display
    document.getElementById('final-threshold').textContent = threshold.toFixed(2) + ' dB';
    document.getElementById('final-frequency').textContent = experimentState.condition.frequency + ' Hz';
    document.getElementById('final-trials').textContent = experimentState.currentTrial;
    
    showStage('stage-completion');

    // Send data to Google Sheets
    sendDataToGoogleSheets(threshold);
}

async function sendDataToGoogleSheets(threshold) {
    const dataToSend = {
        timestamp: new Date().toISOString(),
        subjectID: experimentState.subjectID,
        age: experimentState.demographics.age,
        gender: experimentState.demographics.gender,
        musicalBackground: experimentState.demographics.musicalBackground,
        noiseLevel: experimentState.demographics.noiseLevel,
        frequency: experimentState.condition.frequency,
        pedestal: experimentState.condition.pedestal,
        duration: experimentState.condition.duration,
        bitrate: experimentState.condition.bitrate,
        calculatedThreshold_DL: threshold.toFixed(3),
        totalTrials: experimentState.currentTrial,
        totalReversals: experimentState.reversals.length,
        rawTrialData: JSON.stringify(experimentState.trialHistory)
    };

    try {
        const response = await fetch(CONFIG.GOOGLE_SCRIPT_URL, {
            method: 'POST',
            mode: 'no-cors',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(dataToSend)
        });

        document.getElementById('data-status').textContent = 'Saved Successfully ✓';
        document.getElementById('data-status').style.color = 'var(--success)';
    } catch (error) {
        console.error('Error saving data:', error);
        document.getElementById('data-status').textContent = 'Error Saving Data';
        document.getElementById('data-status').style.color = 'var(--error)';
        
        // Fallback: Download data as JSON
        downloadDataAsJSON(dataToSend);
    }
}

function downloadDataAsJSON(data) {
    const dataStr = JSON.stringify(data, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr);
    const exportFileDefaultName = `psychoacoustic_data_${experimentState.subjectID}.json`;

    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
}

// UI Helper Functions
function showStage(stageId) {
    document.querySelectorAll('.stage').forEach(stage => {
        stage.classList.remove('active');
    });
    document.getElementById(stageId).classList.add('active');
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// Event Listeners
document.getElementById('consent-checkbox').addEventListener('change', function() {
    document.getElementById('consent-proceed-btn').disabled = !this.checked;
});

document.getElementById('calibration-checkbox').addEventListener('change', function() {
    document.getElementById('calibration-proceed-btn').disabled = !this.checked;
});

// Initialize
console.log('Psychoacoustic Experiment Initialized');
console.log('Subject ID will be generated on experiment start');
