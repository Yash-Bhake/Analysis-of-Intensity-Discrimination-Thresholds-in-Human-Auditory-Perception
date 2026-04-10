/**
 * Psychoacoustic Experiment - Stage 2 Factorial Design
 * 2x2 Full Factorial: Frequency (250, 1000 Hz) × ISI (200, 1000 ms)
 * Pure sine wave tones (JND-appropriate stimuli)
 * 2 replications each = 8 blocks total
 */

// Configuration
const CONFIG = {
    GOOGLE_SCRIPT_URL: 'https://script.google.com/macros/s/AKfycbzJxqX9-4ayrhtf_qd7-t0NnzSdNrjlBK7P5hnTXkHddzcn_JWfrFHgPkOjBAzlk9perw/exec',
    STIMULI_PATH: 'stimuli/',
    
    // Adaptive staircase parameters
    INITIAL_DELTA_I: 5.0,  // Starting at 5 dB
    LARGE_STEP: 1.0,       // Large step size until first error
    FINE_STEP: 0.5,        // Fine step size after first error
    MAX_TRIALS: 40,
    TARGET_REVERSALS: 6,
    DISCARD_EARLY_REVERSALS: 2,  // Discard first N reversals (unstable)
    
    BREAK_DURATION: 60,   // 2 minutes in seconds
};

// Factorial Design: 2×2 with 2 replications = 8 blocks
// Factor A: Frequency (spectral)
// Factor B: ISI (temporal)
const FREQUENCIES = [250, 1000];
const ISI_VALUES = [200, 1000];  // Inter-stimulus interval in ms
const REPLICATIONS = 2;

// Generate block order (randomized for each participant)
function generateBlockOrder() {
    const blocks = [];
    
    // Create all treatment combinations with replications
    for (let rep = 0; rep < REPLICATIONS; rep++) {
        for (let freq of FREQUENCIES) {
            for (let isi of ISI_VALUES) {
                blocks.push({
                    frequency: freq,
                    isi: isi,  // ISI as temporal factor
                    replication: rep + 1
                });
            }
        }
    }
    
    // Fisher-Yates shuffle
    for (let i = blocks.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [blocks[i], blocks[j]] = [blocks[j], blocks[i]];
    }
    
    return blocks;
}

// Global state
let experimentState = {
    participantName: null,
    participantID: null,
    blockOrder: [],
    currentBlockIndex: 0,
    allBlockData: [],
    
    // Current block state
    currentBlock: null,
    currentTrial: 0,
    deltaI: CONFIG.INITIAL_DELTA_I,
    stepSize: CONFIG.LARGE_STEP,
    inFineRegion: false,
    firstErrorMade: false,
    reversals: [],
    trialHistory: [],
    lastDirection: null,
    currentCorrectAnswer: null,
    
    audioContext: null,
    tonesToPlay: null,
    tonesLoaded: false
};

// Audio handling
class AudioPlayer {
    constructor() {
        this.context = new (window.AudioContext || window.webkitAudioContext)();
    }

    async loadAudioFile(filename) {
        const url = CONFIG.STIMULI_PATH + filename;
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`Failed to load ${url} (HTTP ${response.status})`);
        }
        const arrayBuffer = await response.arrayBuffer();
        return await this.context.decodeAudioData(arrayBuffer);
    }

    async playBuffer(audioBuffer, when = 0) {
        const source = this.context.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(this.context.destination);
        source.start(when);
        return new Promise(resolve => {
            source.onended = resolve;
        });
    }

    getContext() {
        return this.context;
    }
}

const audioPlayer = new AudioPlayer();

// localStorage safety keys
const STORAGE_KEYS = {
    SESSION_PREFIX: 'psycho_stage2_session_',
    LAST_SESSION_KEY: 'psycho_stage2_last_session_key',
    LAST_COMPLETED_JSON: 'psycho_stage2_last_completed_json',
    LAST_COMPLETED_CSV: 'psycho_stage2_last_completed_csv'
};

// Utility functions
function generateParticipantID() {
    return 'P' + Date.now().toString(36) + Math.random().toString(36).substr(2, 5);
}

function roundToStep(value, step) {
    return Math.round(value / step) * step;
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function getSessionStorageKey() {
    return `${STORAGE_KEYS.SESSION_PREFIX}${experimentState.participantID || 'unknown'}`;
}

function safeLocalStorageSet(key, value) {
    try {
        localStorage.setItem(key, value);
    } catch (error) {
        console.warn(`localStorage write failed for key ${key}:`, error);
    }
}

function buildCSVContent(blocks, participantID, participantName) {
    const headers = [
        'participant_id', 'participant_name', 'block_number',
        'frequency_hz', 'isi_ms', 'replication',
        'threshold_db', 'total_trials', 'total_reversals',
        'discarded_reversals', 'usable_reversals', 'timestamp'
    ];

    const rows = blocks.map(b => [
        participantID,
        participantName,
        b.blockNumber,
        b.frequency,
        b.isi,
        b.replication,
        Number(b.threshold).toFixed(4),
        b.totalTrials,
        b.totalReversals,
        b.discardedReversals,
        b.usableReversals,
        new Date().toISOString()
    ]);

    return [headers, ...rows].map(r => r.join(',')).join('\n');
}

function persistCheckpoint(reason = 'checkpoint') {
    const sessionKey = getSessionStorageKey();
    const snapshot = {
        savedAt: new Date().toISOString(),
        reason,
        schemaVersion: 'stage2_freq_isi_v1',
        participantID: experimentState.participantID,
        participantName: experimentState.participantName,
        currentBlockIndex: experimentState.currentBlockIndex,
        completedBlocks: experimentState.allBlockData.length,
        allBlockData: experimentState.allBlockData
    };

    safeLocalStorageSet(sessionKey, JSON.stringify(snapshot));
    safeLocalStorageSet(STORAGE_KEYS.LAST_SESSION_KEY, sessionKey);
}

function persistCompletedBackup() {
    const completed = {
        savedAt: new Date().toISOString(),
        schemaVersion: 'stage2_freq_isi_v1',
        participantID: experimentState.participantID,
        participantName: experimentState.participantName,
        totalBlocks: experimentState.allBlockData.length,
        allBlockData: experimentState.allBlockData
    };

    safeLocalStorageSet(STORAGE_KEYS.LAST_COMPLETED_JSON, JSON.stringify(completed));
    safeLocalStorageSet(
        STORAGE_KEYS.LAST_COMPLETED_CSV,
        buildCSVContent(completed.allBlockData, completed.participantID, completed.participantName)
    );
}

function showStage(stageId) {
    document.querySelectorAll('.stage').forEach(stage => {
        stage.classList.remove('active');
    });
    document.getElementById(stageId).classList.add('active');
}

// UI Control Functions
function proceedFromConsent() {
    if (!document.getElementById('consent-checkbox').checked) return;
    showStage('stage-name');
}

function proceedFromName() {
    const name = document.getElementById('participant-name').value.trim();
    
    if (name) {
        experimentState.participantName = name;
        experimentState.participantID = generateParticipantID();
    } else {
        experimentState.participantName = 'Anonymous';
        experimentState.participantID = generateParticipantID();
    }

    // Start a recoverable local checkpoint for this participant session.
    persistCheckpoint('session_started');
    
    showStage('stage-calibration');
}

async function playCalibrationTone() {
    const btn = document.getElementById('calibration-play-btn');
    btn.disabled = true;
    btn.textContent = 'Playing...';

    try {
        let buffer;
        try {
            buffer = await audioPlayer.loadAudioFile('calibration_tone.mp3');
        } catch (primaryError) {
            console.warn('Calibration file missing, using fallback tone:', primaryError);
            // Fallback keeps calibration usable even if dedicated file is absent on hosting.
            buffer = await audioPlayer.loadAudioFile('freq1000_delta0.0.mp3');
        }
        await audioPlayer.playBuffer(buffer);
        
        setTimeout(() => {
            btn.disabled = false;
            btn.textContent = '🔊 Play Calibration Tone';
        }, 500);
    } catch (error) {
        console.error('Error playing calibration tone:', error);
        alert('Error loading calibration tone. Please ensure the stimuli folder is accessible and includes required MP3 files.');
        btn.disabled = false;
        btn.textContent = '🔊 Play Calibration Tone';
    }
}

function startExperiment() {
    if (!document.getElementById('calibration-checkbox').checked) return;
    
    // Generate randomized block order
    experimentState.blockOrder = generateBlockOrder();
    
    console.log('Block order:', experimentState.blockOrder);
    
    showStage('stage-instructions');
}

function startFirstBlock() {
    experimentState.currentBlockIndex = 0;
    initializeBlock();
    showStage('stage-experiment');
    prepareTrialTones();
}

function initializeBlock() {
    const blockNum = experimentState.currentBlockIndex;
    experimentState.currentBlock = experimentState.blockOrder[blockNum];
    
    // Reset block state
    experimentState.currentTrial = 0;
    experimentState.deltaI = CONFIG.INITIAL_DELTA_I;
    experimentState.stepSize = CONFIG.LARGE_STEP;
    experimentState.inFineRegion = false;
    experimentState.firstErrorMade = false;
    experimentState.correctStreak = 0;
    experimentState.reversals = [];
    experimentState.trialHistory = [];
    experimentState.lastDirection = null;
    
    // Update UI
    document.getElementById('block-number').textContent = `${blockNum + 1}/8`;
    
    console.log(`Starting Block ${blockNum + 1}:`, experimentState.currentBlock);
}

// File naming
function getStandardFilename() {
    const { frequency } = experimentState.currentBlock;
    return `freq${frequency}_delta0.0.mp3`;
}

function getComparisonFilename(deltaI) {
    const { frequency } = experimentState.currentBlock;
    return `freq${frequency}_delta${deltaI.toFixed(1)}.mp3`;
}

// Trial preparation and execution
async function prepareTrialTones() {
    experimentState.currentTrial++;
    experimentState.tonesLoaded = false;
    
    // Update UI
    document.getElementById('trial-number').textContent = `${experimentState.currentTrial}/40`;
    updateDebugDisplay();
    document.getElementById('playback-status').textContent = 'Loading sounds...';
    document.getElementById('play-trial-btn').disabled = true;
    document.getElementById('response-buttons').style.display = 'none';
    
    const progress = (experimentState.currentTrial / CONFIG.MAX_TRIALS) * 100;
    document.getElementById('progress-fill').style.width = `${progress}%`;
    
    try {
        // Load audio files
        const standardFile = getStandardFilename();
        const comparisonFile = getComparisonFilename(experimentState.deltaI);
        
        const standardBuffer = await audioPlayer.loadAudioFile(standardFile);
        const comparisonBuffer = await audioPlayer.loadAudioFile(comparisonFile);
        
        // Randomize order
        const comparisonFirst = Math.random() < 0.5;
        experimentState.tonesToPlay = {
            buffer1: comparisonFirst ? comparisonBuffer : standardBuffer,
            buffer2: comparisonFirst ? standardBuffer : comparisonBuffer
        };
        experimentState.currentCorrectAnswer = comparisonFirst ? 1 : 2;
        experimentState.tonesLoaded = true;
        
        // Enable play button
        document.getElementById('playback-status').textContent = 'Click "Play Tones" when ready';
        document.getElementById('play-trial-btn').disabled = false;
        
    } catch (error) {
        console.error('Error loading trial sounds:', error);
        document.getElementById('playback-status').textContent = 'Error loading sounds';
    }
}

async function playTrialTones() {
    if (!experimentState.tonesLoaded) return;
    
    const playBtn = document.getElementById('play-trial-btn');
    playBtn.disabled = true;
    document.getElementById('response-buttons').style.display = 'none';
    
    const { buffer1, buffer2 } = experimentState.tonesToPlay;
    const isiDuration = experimentState.currentBlock.isi;  // Use block-specific ISI
    
    try {
        // Play Sound 1
        document.getElementById('playback-status').textContent = '🔊 Sound 1 Playing...';
        document.getElementById('playback-status').className = 'playback-status playing';
        await audioPlayer.playBuffer(buffer1);
        
        // Silence (using block-specific ISI)
        document.getElementById('playback-status').textContent = 'Silence...';
        document.getElementById('playback-status').className = 'playback-status';
        await sleep(isiDuration);
        
        // Play Sound 2
        document.getElementById('playback-status').textContent = '🔊 Sound 2 Playing...';
        document.getElementById('playback-status').className = 'playback-status playing';
        await audioPlayer.playBuffer(buffer2);
        
        // Show response buttons
        await sleep(200);
        document.getElementById('playback-status').textContent = 'Which sound was LOUDER?';
        document.getElementById('playback-status').className = 'playback-status';
        document.getElementById('response-buttons').style.display = 'flex';
        playBtn.disabled = false;
        
    } catch (error) {
        console.error('Error playing tones:', error);
        playBtn.disabled = false;
    }
}

function respondSound(choice) {
    const correct = (choice === experimentState.currentCorrectAnswer);
    
    // Record trial data
    const trialData = {
        trialNumber: experimentState.currentTrial,
        deltaI: experimentState.deltaI,
        stepSize: experimentState.stepSize,
        inFineRegion: experimentState.inFineRegion,
        response: choice,
        correctAnswer: experimentState.currentCorrectAnswer,
        correct: correct,
        timestamp: new Date().toISOString()
    };
    experimentState.trialHistory.push(trialData);
    
    // Update staircase
    updateStaircase(correct);
    
    // Check termination
    if (experimentState.reversals.length >= CONFIG.TARGET_REVERSALS || 
        experimentState.currentTrial >= CONFIG.MAX_TRIALS) {
        completeBlock();
    } else {
        setTimeout(prepareTrialTones, 500);
    }
}

// Adaptive staircase with two-phase step sizes
function updateStaircase(correct) {
    let newDeltaI = experimentState.deltaI;
    let direction = null;
    
    if (!experimentState.firstErrorMade) {
        // PHASE 1: Before first error - use large steps, 3-down rule
        if (correct) {
            experimentState.correctStreak = (experimentState.correctStreak || 0) + 1;
            
            // 3 consecutive correct → decrease (make harder)
            if (experimentState.correctStreak >= 3) {
                newDeltaI = Math.max(0.5, experimentState.deltaI - CONFIG.LARGE_STEP);
                direction = 'down';
                experimentState.correctStreak = 0;  // Reset streak
            }
        } else {
            // First error encountered!
            experimentState.firstErrorMade = true;
            experimentState.inFineRegion = true;
            experimentState.stepSize = CONFIG.FINE_STEP;
            experimentState.correctStreak = 0;
            
            // Increase deltaI (make easier)
            newDeltaI = Math.min(12.0, experimentState.deltaI + CONFIG.FINE_STEP);
            direction = 'up';
        }
    } else {
        // PHASE 2: After first error - use fine steps, 3-down 1-up
        if (correct) {
            experimentState.correctStreak = (experimentState.correctStreak || 0) + 1;
            
            // 3 consecutive correct → decrease (make harder)
            if (experimentState.correctStreak >= 3) {
                newDeltaI = Math.max(0.5, experimentState.deltaI - CONFIG.FINE_STEP);
                direction = 'down';
                experimentState.correctStreak = 0;  // Reset streak
            }
        } else {
            // 1 incorrect → increase (make easier)
            newDeltaI = Math.min(12.0, experimentState.deltaI + CONFIG.FINE_STEP);
            direction = 'up';
            experimentState.correctStreak = 0;  // Reset streak on error
        }
    }
    
    // Detect reversal (only when direction actually changes)
    if (direction && experimentState.lastDirection && direction !== experimentState.lastDirection) {
        experimentState.reversals.push({
            trial: experimentState.currentTrial,
            deltaI: experimentState.deltaI,
            inFineRegion: experimentState.inFineRegion
        });
    }
    
    // Update direction only if we actually moved
    if (direction) {
        experimentState.lastDirection = direction;
    }
    
    experimentState.deltaI = roundToStep(newDeltaI, 0.5);
    updateDebugDisplay();
}

function completeBlock() {
    // Calculate threshold from additional reversals only
    // Discard first N reversals as they are unstable (initialization phase)
    const usableReversals = experimentState.reversals.slice(CONFIG.DISCARD_EARLY_REVERSALS);
    
    const threshold = usableReversals.length > 0
        ? usableReversals.reduce((sum, r) => sum + r.deltaI, 0) / usableReversals.length
        : experimentState.deltaI;
    
    // Store block data
    const blockData = {
        blockNumber: experimentState.currentBlockIndex + 1,
        frequency: experimentState.currentBlock.frequency,
        isi: experimentState.currentBlock.isi,  // ISI as factor
        replication: experimentState.currentBlock.replication,
        threshold: threshold,
        thresholdUnit: 'dB',
        totalTrials: experimentState.currentTrial,
        totalReversals: experimentState.reversals.length,
        discardedReversals: CONFIG.DISCARD_EARLY_REVERSALS,
        usableReversals: usableReversals.length,
        trialHistory: experimentState.trialHistory
    };
    
    experimentState.allBlockData.push(blockData);

    // Persist progress after each completed block.
    persistCheckpoint(`block_${blockData.blockNumber}_completed`);
    
    console.log(`Block ${experimentState.currentBlockIndex + 1} complete. Threshold: ${threshold.toFixed(3)} dB (from ${usableReversals.length} usable reversals)`);
    
    // Save this block to Google Sheets immediately (don't wait for all 8 blocks)
    saveBlockToGoogleSheets(blockData);
    
    // Check if more blocks remain
    if (experimentState.currentBlockIndex < 7) {
        // Take a break
        showBreakScreen();
    } else {
        // Experiment complete
        completeExperiment();
    }
}

function showBreakScreen() {
    const completedBlock = experimentState.currentBlockIndex + 1;
    const nextBlock = completedBlock + 1;
    
    document.getElementById('break-completed-block').textContent = completedBlock;
    document.getElementById('next-block-num').textContent = nextBlock;
    
    showStage('stage-break');
    
    // Start countdown timer
    let timeLeft = CONFIG.BREAK_DURATION;
    const continueBtn = document.getElementById('continue-btn');
    continueBtn.disabled = true;
    
    const timerInterval = setInterval(() => {
        const minutes = Math.floor(timeLeft / 60);
        const seconds = timeLeft % 60;
        document.getElementById('break-timer').textContent = 
            `${minutes}:${seconds.toString().padStart(2, '0')}`;
        
        timeLeft--;
        
        if (timeLeft < 0) {
            clearInterval(timerInterval);
            continueBtn.disabled = false;
            document.getElementById('break-timer').textContent = 'Ready!';
        }
    }, 1000);
}

function continueToNextBlock() {
    experimentState.currentBlockIndex++;
    initializeBlock();
    showStage('stage-experiment');
    prepareTrialTones();
}

async function completeExperiment() {
    // Calculate total trials
    const totalTrials = experimentState.allBlockData.reduce((sum, b) => sum + b.totalTrials, 0);
    document.getElementById('total-trials').textContent = totalTrials;
    
    showStage('stage-completion');

    // Persist final session state and completed backups before any network/download step.
    persistCheckpoint('experiment_completed');
    persistCompletedBackup();
    
    // Auto-download CSV backup (analysis-ready format matching notebook schema)
    downloadDataAsCSV();
    
    document.getElementById('data-status').textContent =
        'Data saved \u2713  Each block was sent to Google Sheets automatically. CSV also downloaded.';
    document.getElementById('data-status').style.color = 'var(--accent-primary)';
}

// Save a single completed block to Google Sheets immediately.
// Wraps the block in an array so the Apps Script doPost handler
// (which iterates over data.blockData[]) works with 1 or 8 entries.
async function saveBlockToGoogleSheets(blockData) {
    const payload = {
        timestamp: new Date().toISOString(),
        participantID: experimentState.participantID,
        participantName: experimentState.participantName,
        blockData: [blockData],   // single-block array
        totalBlocks: 8,
        schemaVersion: 'stage2_freq_isi_v1'
    };
    
    try {
        await fetch(CONFIG.GOOGLE_SCRIPT_URL, {
            method: 'POST',
            mode: 'no-cors',
            headers: { 'Content-Type': 'text/plain;charset=utf-8' },
            body: JSON.stringify(payload)
        });
        console.log(`Block ${blockData.blockNumber} data sent to Google Sheets`);
    } catch (error) {
        // Non-fatal: data is still in experimentState.allBlockData and the
        // CSV download at the end of the session will preserve it.
        console.error(`Failed to send block ${blockData.blockNumber} to Sheets:`, error);
    }
}

// Download all block data as a CSV that matches the notebook/analysis schema.
// Column order mirrors: participant_id, block_number, frequency_hz, isi_ms,
// replication, threshold_db, total_trials, total_reversals, usable_reversals
function downloadDataAsCSV() {
    const csvContent = buildCSVContent(
        experimentState.allBlockData,
        experimentState.participantID,
        experimentState.participantName
    );
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    
    const link = document.createElement('a');
    link.href = url;
    link.download = `psychoacoustic_${experimentState.participantID}_${Date.now()}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    
    console.log('CSV backup downloaded.');
}

function downloadLastCompletedBackupFromLocalStorage() {
    const csvContent = localStorage.getItem(STORAGE_KEYS.LAST_COMPLETED_CSV);
    if (!csvContent) {
        alert('No completed local backup found in browser storage.');
        return;
    }

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `psychoacoustic_recovered_${Date.now()}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

// Event listeners
document.getElementById('consent-checkbox').addEventListener('change', function() {
    document.getElementById('consent-proceed-btn').disabled = !this.checked;
});

document.getElementById('calibration-checkbox').addEventListener('change', function() {
    document.getElementById('calibration-proceed-btn').disabled = !this.checked;
});

console.log('Psychoacoustic Experiment - Stage 2 Initialized');
console.log('Factorial Design: 2 Frequencies × 2 ISI Values × 2 Replications = 8 Blocks');
console.log('Factor A (Spectral): Frequency - 250 Hz, 1000 Hz');
console.log('Factor B (Temporal): ISI - 200 ms, 1000 ms');
console.log('Tone Type: Pure Sine Waves (JND-appropriate)');
console.log('Reversal Handling: Discard first 2 reversals, average remaining reversals');
console.log('Safety: localStorage checkpoints enabled. Recovery command: downloadLastCompletedBackupFromLocalStorage()');

// Debug stats toggle
let debugStatsVisible = true;

function toggleDebugStats() {
    debugStatsVisible = !debugStatsVisible;
    
    const statsToToggle = ['freq-stat', 'isi-stat', 'delta-stat', 'reversal-stat'];
    const btn = document.getElementById('debug-toggle-btn');
    
    statsToToggle.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.style.display = debugStatsVisible ? 'block' : 'none';
        }
    });
    
    btn.textContent = debugStatsVisible ? '🔒 Hide Debug Stats' : '🔍 Show Debug Stats';
    
    // Update values if visible
    if (debugStatsVisible && experimentState.currentBlock) {
        updateDebugDisplay();
    }
}

function updateDebugDisplay() {
    if (!debugStatsVisible) return;
    
    document.getElementById('current-freq').textContent = 
        experimentState.currentBlock.frequency + ' Hz';
    document.getElementById('current-isi').textContent = 
        experimentState.currentBlock.isi + ' ms';
    document.getElementById('current-delta').textContent = 
        experimentState.deltaI.toFixed(1) + ' dB';
    document.getElementById('reversal-count').textContent = 
        `${experimentState.reversals.length}/6`;
}
