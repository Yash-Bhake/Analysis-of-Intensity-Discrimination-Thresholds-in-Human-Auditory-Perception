/**
 * Psychoacoustic Experiment - Stage 2 Factorial Design
 * 2x2 Full Factorial: Frequency (250, 1000 Hz) × Tone Type (sine, triangle)
 * 2 replications each = 8 blocks total
 */

// Configuration
const CONFIG = {
    GOOGLE_SCRIPT_URL: 'https://script.google.com/macros/s/AKfycbwwYdWSiwyouO2etOI9xftWl-_js4lNQtRwYGjMb0-WE5Qc2vQW3o0Wqu2fjxBu2Cr_9A/exec',
    STIMULI_PATH: 'stimuli/',
    
    // Adaptive staircase parameters
    INITIAL_DELTA_I: 5.0,  // Starting at 5 dB
    LARGE_STEP: 1.5,       // Large step size until first error
    FINE_STEP: 0.5,        // Fine step size after first error
    MAX_TRIALS: 40,
    TARGET_REVERSALS: 6,
    ISI: 500,              // Inter-stimulus interval in ms
    
    BREAK_DURATION: 120,   // 2 minutes in seconds
};

// Factorial Design: 2×2 with 2 replications = 8 blocks
const FREQUENCIES = [250, 1000];
const TONE_TYPES = ['sine', 'triangle'];
const REPLICATIONS = 2;

// Generate block order (randomized for each participant)
function generateBlockOrder() {
    const blocks = [];
    
    // Create all treatment combinations with replications
    for (let rep = 0; rep < REPLICATIONS; rep++) {
        for (let freq of FREQUENCIES) {
            for (let tone of TONE_TYPES) {
                blocks.push({
                    frequency: freq,
                    toneType: tone,
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
        const response = await fetch(CONFIG.STIMULI_PATH + filename);
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
            btn.textContent = '🔊 Play Calibration Tone';
        }, 500);
    } catch (error) {
        console.error('Error playing calibration tone:', error);
        alert('Error loading calibration tone. Please ensure the stimuli folder is accessible.');
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
    experimentState.reversals = [];
    experimentState.trialHistory = [];
    experimentState.lastDirection = null;
    
    // Update UI
    document.getElementById('block-number').textContent = `${blockNum + 1}/8`;
    
    console.log(`Starting Block ${blockNum + 1}:`, experimentState.currentBlock);
}

// File naming
function getStandardFilename() {
    const { frequency, toneType } = experimentState.currentBlock;
    return `freq${frequency}_${toneType}_delta0.0.mp3`;
}

function getComparisonFilename(deltaI) {
    const { frequency, toneType } = experimentState.currentBlock;
    return `freq${frequency}_${toneType}_delta${deltaI.toFixed(1)}.mp3`;
}

// Trial preparation and execution
async function prepareTrialTones() {
    experimentState.currentTrial++;
    experimentState.tonesLoaded = false;
    
    // Update UI
    document.getElementById('trial-number').textContent = `${experimentState.currentTrial}/40`;
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
    
    try {
        // Play Sound 1
        document.getElementById('playback-status').textContent = '🔊 Sound 1 Playing...';
        document.getElementById('playback-status').className = 'playback-status playing';
        await audioPlayer.playBuffer(buffer1);
        
        // Silence
        document.getElementById('playback-status').textContent = 'Silence...';
        document.getElementById('playback-status').className = 'playback-status';
        await sleep(CONFIG.ISI);
        
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
    
    if (correct) {
        // Correct response: decrease deltaI (make harder)
        newDeltaI = Math.max(0.5, experimentState.deltaI - experimentState.stepSize);
        direction = 'down';
    } else {
        // Incorrect response
        if (!experimentState.firstErrorMade) {
            // First error: switch to fine region
            experimentState.firstErrorMade = true;
            experimentState.inFineRegion = true;
            experimentState.stepSize = CONFIG.FINE_STEP;
        }
        
        // Increase deltaI (make easier)
        newDeltaI = Math.min(12.0, experimentState.deltaI + experimentState.stepSize);
        direction = 'up';
    }
    
    // Detect reversal
    if (direction && experimentState.lastDirection && direction !== experimentState.lastDirection) {
        experimentState.reversals.push({
            trial: experimentState.currentTrial,
            deltaI: experimentState.deltaI,
            inFineRegion: experimentState.inFineRegion
        });
    }
    
    experimentState.lastDirection = direction;
    experimentState.deltaI = roundToStep(newDeltaI, 0.5);
}

function completeBlock() {
    // Calculate threshold from fine-region reversals only
    const fineReversals = experimentState.reversals.filter(r => r.inFineRegion);
    const threshold = fineReversals.length > 0
        ? fineReversals.reduce((sum, r) => sum + r.deltaI, 0) / fineReversals.length
        : experimentState.deltaI;
    
    // Store block data
    const blockData = {
        blockNumber: experimentState.currentBlockIndex + 1,
        frequency: experimentState.currentBlock.frequency,
        toneType: experimentState.currentBlock.toneType,
        replication: experimentState.currentBlock.replication,
        threshold: threshold,
        totalTrials: experimentState.currentTrial,
        totalReversals: experimentState.reversals.length,
        fineReversals: fineReversals.length,
        trialHistory: experimentState.trialHistory
    };
    
    experimentState.allBlockData.push(blockData);
    
    console.log(`Block ${experimentState.currentBlockIndex + 1} complete. Threshold: ${threshold.toFixed(3)} dB`);
    
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
    
    // Send data to Google Sheets
    await sendDataToGoogleSheets();
}

async function sendDataToGoogleSheets() {
    const dataToSend = {
        timestamp: new Date().toISOString(),
        participantID: experimentState.participantID,
        participantName: experimentState.participantName,
        blockData: experimentState.allBlockData,
        totalBlocks: 8
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
        document.getElementById('data-status').style.color = 'var(--accent-success)';
    } catch (error) {
        console.error('Error saving data:', error);
        document.getElementById('data-status').textContent = 'Error - Download Backup';
        document.getElementById('data-status').style.color = '#ef4444';
        
        // Fallback: download as JSON
        downloadDataAsJSON(dataToSend);
    }
}

function downloadDataAsJSON(data) {
    const dataStr = JSON.stringify(data, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr);
    const exportFileDefaultName = `psychoacoustic_data_${experimentState.participantID}.json`;
    
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
}

// Event listeners
document.getElementById('consent-checkbox').addEventListener('change', function() {
    document.getElementById('consent-proceed-btn').disabled = !this.checked;
});

document.getElementById('calibration-checkbox').addEventListener('change', function() {
    document.getElementById('calibration-proceed-btn').disabled = !this.checked;
});

console.log('Psychoacoustic Experiment - Stage 2 Initialized');
console.log('Factorial Design: 2 Frequencies × 2 Tone Types × 2 Replications = 8 Blocks');