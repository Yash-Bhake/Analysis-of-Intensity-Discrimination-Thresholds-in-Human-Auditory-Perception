/**
 * Google Apps Script for Psychoacoustic Experiment - Stage 2
 * Logs data from 2×2 factorial design with 2 replications (8 blocks per participant)
 * Design: Frequency (250, 1000 Hz) × ISI (200, 1000 ms)
 */

// Configuration
const SHEET_ID = '1X2zVVpB6ex1I2h4zX0y8mFPksqEj3tQ7rZm1FIuaiAc';
const SHEET_NAME = 'Experimental Data';

/**
 * Handle POST requests from the experiment
 */
function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);
    const sheet = getOrCreateSheet();
    
    // Append one row per block (8 rows per participant)
    for (let blockData of data.blockData) {
      appendBlockToSheet(sheet, data, blockData);
    }
    
    return ContentService
      .createTextOutput(JSON.stringify({ 'result': 'success', 'blocks': data.blockData.length }))
      .setMimeType(ContentService.MimeType.JSON);
      
  } catch (error) {
    Logger.log('Error: ' + error.toString());
    return ContentService
      .createTextOutput(JSON.stringify({ 'result': 'error', 'error': error.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * Handle GET requests (for testing)
 */
function doGet(e) {
  return ContentService
    .createTextOutput('Psychoacoustic Experiment Data Logger - Stage 2 (Running)')
    .setMimeType(ContentService.MimeType.TEXT);
}

/**
 * Get existing sheet or create new one with headers
 */
function getOrCreateSheet() {
  const ss = SpreadsheetApp.openById(SHEET_ID);
  let sheet = ss.getSheetByName(SHEET_NAME);
  
  if (!sheet) {
    sheet = ss.insertSheet(SHEET_NAME);
    
    // Column headers for factorial design
    const headers = [
      'Timestamp',
      'Participant ID',
      'Participant Name',
      'Block Number',
      'Frequency (Hz)',
      'ISI (ms)',
      'Replication',
      'Threshold (dB)',
      'Total Trials',
      'Total Reversals',
      'Discarded Reversals',
      'Usable Reversals',
      'Raw Trial Data'
    ];
    
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    
    // Format header row
    sheet.getRange(1, 1, 1, headers.length)
      .setBackground('#3b82f6')
      .setFontColor('#ffffff')
      .setFontWeight('bold')
      .setHorizontalAlignment('center');
    
    // Freeze header row
    sheet.setFrozenRows(1);
    
    // Set column widths
    sheet.setColumnWidth(1, 180);  // Timestamp
    sheet.setColumnWidth(2, 120);  // Participant ID
    sheet.setColumnWidth(3, 150);  // Participant Name
    sheet.setColumnWidth(4, 80);   // Block Number
    sheet.setColumnWidth(5, 100);  // Frequency
    sheet.setColumnWidth(6, 100);  // ISI
    sheet.setColumnWidth(7, 90);   // Replication
    sheet.setColumnWidth(8, 110);  // Threshold
    sheet.setColumnWidth(13, 300); // Raw Trial Data
  }
  
  return sheet;
}

/**
 * Append one block's data to the sheet
 */
function appendBlockToSheet(sheet, sessionData, blockData) {
  const row = [
    sessionData.timestamp,
    sessionData.participantID || '',
    sessionData.participantName || '',
    blockData.blockNumber || '',
    blockData.frequency || '',
    blockData.isi || '',
    blockData.replication || '',
    blockData.threshold || '',
    blockData.totalTrials || '',
    blockData.totalReversals || '',
    blockData.discardedReversals || 2,
    blockData.usableReversals || '',
    JSON.stringify(blockData.trialHistory || [])
  ];
  
  sheet.appendRow(row);
  
  const lastRow = sheet.getLastRow();
  
  // Alternate row colors
  if (lastRow % 2 === 0) {
    sheet.getRange(lastRow, 1, 1, row.length).setBackground('#f8f9fa');
  }
  
  // Format threshold as number with 3 decimals
  if (blockData.threshold) {
    sheet.getRange(lastRow, 8).setNumberFormat('0.000');
  }
}

/**
 * Test function - run from Apps Script editor
 */
function testDataLogging() {
  const testData = {
    timestamp: new Date().toISOString(),
    participantID: 'TEST_P123',
    participantName: 'Test Subject',
    totalBlocks: 8,
    blockData: [
      {
        blockNumber: 1,
        frequency: 250,
        isi: 200,
        replication: 1,
        threshold: 3.456,
        totalTrials: 28,
        totalReversals: 6,
        discardedReversals: 2,
        usableReversals: 4,
        trialHistory: [{"trial": 1, "correct": true}]
      },
      {
        blockNumber: 2,
        frequency: 1000,
        isi: 1000,
        replication: 1,
        threshold: 2.789,
        totalTrials: 31,
        totalReversals: 6,
        discardedReversals: 2,
        usableReversals: 4,
        trialHistory: [{"trial": 1, "correct": false}]
      }
    ]
  };
  
  const sheet = getOrCreateSheet();
  
  for (let blockData of testData.blockData) {
    appendBlockToSheet(sheet, testData, blockData);
  }
  
  Logger.log('Test data logged successfully!');
  Logger.log('Check your sheet: ' + SpreadsheetApp.openById(SHEET_ID).getUrl());
}

/**
 * Create summary statistics for analysis
 */
function createSummarySheet() {
  const ss = SpreadsheetApp.openById(SHEET_ID);
  const dataSheet = ss.getSheetByName(SHEET_NAME);
  
  if (!dataSheet) {
    Logger.log('No data sheet found!');
    return;
  }
  
  let summarySheet = ss.getSheetByName('Summary Statistics');
  if (!summarySheet) {
    summarySheet = ss.insertSheet('Summary Statistics');
  }
  
  summarySheet.clear();
  
  // Title
  summarySheet.getRange('A1').setValue('Factorial Design Summary Statistics');
  summarySheet.getRange('A1').setFontSize(14).setFontWeight('bold');
  
  // Overall stats
  const lastRow = dataSheet.getLastRow();
  summarySheet.getRange('A3').setValue('Total Participants:');
  summarySheet.getRange('B3').setFormula(`=COUNTA(UNIQUE('${SHEET_NAME}'!B2:B))`);
  
  summarySheet.getRange('A4').setValue('Total Blocks Recorded:');
  summarySheet.getRange('B4').setValue(lastRow - 1);
  
  // Mean threshold by treatment combination
  summarySheet.getRange('A6').setValue('Mean Threshold by Treatment Combination');
  summarySheet.getRange('A6').setFontWeight('bold');
  
  const headers = ['Frequency', 'ISI (ms)', 'Mean Threshold (dB)', 'Std Dev', 'N'];
  summarySheet.getRange(7, 1, 1, headers.length).setValues([headers]);
  summarySheet.getRange(7, 1, 1, headers.length).setFontWeight('bold');
  
  let row = 8;
  const treatments = [
    [250, 200],
    [250, 1000],
    [1000, 200],
    [1000, 1000]
  ];
  
  treatments.forEach(([freq, isi]) => {
    summarySheet.getRange(row, 1).setValue(freq);
    summarySheet.getRange(row, 2).setValue(isi);
    
    // Use AVERAGEIFS and other formulas
    const avgFormula = `=AVERAGEIFS('${SHEET_NAME}'!H:H,'${SHEET_NAME}'!E:E,${freq},'${SHEET_NAME}'!F:F,${isi})`;
    const stdFormula = `=STDEV.S(FILTER('${SHEET_NAME}'!H:H,('${SHEET_NAME}'!E:E=${freq})*('${SHEET_NAME}'!F:F=${isi})))`;
    const countFormula = `=COUNTIFS('${SHEET_NAME}'!E:E,${freq},'${SHEET_NAME}'!F:F,${isi})`;
    
    summarySheet.getRange(row, 3).setFormula(avgFormula).setNumberFormat('0.000');
    summarySheet.getRange(row, 4).setFormula(stdFormula).setNumberFormat('0.000');
    summarySheet.getRange(row, 5).setFormula(countFormula);
    
    row++;
  });
  
  // Main effects
  summarySheet.getRange('A13').setValue('Main Effect: Frequency');
  summarySheet.getRange('A13').setFontWeight('bold');
  
  summarySheet.getRange('A14').setValue('250 Hz Mean:');
  summarySheet.getRange('B14').setFormula(`=AVERAGEIF('${SHEET_NAME}'!E:E,250,'${SHEET_NAME}'!H:H)`).setNumberFormat('0.000');
  
  summarySheet.getRange('A15').setValue('1000 Hz Mean:');
  summarySheet.getRange('B15').setFormula(`=AVERAGEIF('${SHEET_NAME}'!E:E,1000,'${SHEET_NAME}'!H:H)`).setNumberFormat('0.000');
  
  summarySheet.getRange('A17').setValue('Main Effect: ISI');
  summarySheet.getRange('A17').setFontWeight('bold');
  
  summarySheet.getRange('A18').setValue('200 ms Mean:');
  summarySheet.getRange('B18').setFormula(`=AVERAGEIF('${SHEET_NAME}'!F:F,200,'${SHEET_NAME}'!H:H)`).setNumberFormat('0.000');
  
  summarySheet.getRange('A19').setValue('1000 ms Mean:');
  summarySheet.getRange('B19').setFormula(`=AVERAGEIF('${SHEET_NAME}'!F:F,1000,'${SHEET_NAME}'!H:H)`).setNumberFormat('0.000');
  
  Logger.log('Summary sheet created!');
}