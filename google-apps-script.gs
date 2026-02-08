/**
 * Google Apps Script for Psychoacoustic Experiment Data Logging
 * 
 * SETUP INSTRUCTIONS:
 * 1. Create a new Google Sheet
 * 2. Click Extensions > Apps Script
 * 3. Delete any code in the editor and paste this entire script
 * 4. Click "Deploy" > "New deployment"
 * 5. Select type: "Web app"
 * 6. Set "Execute as": Me
 * 7. Set "Who has access": Anyone
 * 8. Click "Deploy"
 * 9. Copy the web app URL
 * 10. Paste the URL into the CONFIG.GOOGLE_SCRIPT_URL in experiment.js
 * 11. Replace 'YOUR_SHEET_ID_HERE' below with your Google Sheet ID
 *     (Find this in the URL: https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID_HERE/edit)
 */

// Configuration
const SHEET_ID = '1X2zVVpB6ex1I2h4zX0y8mFPksqEj3tQ7rZm1FIuaiAc'; // Replace with your Google Sheet ID
const SHEET_NAME = 'Experimental Data'; // Name of the sheet tab

/**
 * Handle POST requests from the experiment
 */
function doPost(e) {
  try {
    // Parse the incoming JSON data
    const data = JSON.parse(e.postData.contents);
    
    // Get or create the sheet
    const sheet = getOrCreateSheet();
    
    // Append the data
    appendDataToSheet(sheet, data);
    
    // Return success response
    return ContentService
      .createTextOutput(JSON.stringify({ 'result': 'success', 'row': sheet.getLastRow() }))
      .setMimeType(ContentService.MimeType.JSON);
      
  } catch (error) {
    // Return error response
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
    .createTextOutput('Psychoacoustic Experiment Data Logger is running. Use POST to submit data.')
    .setMimeType(ContentService.MimeType.TEXT);
}

/**
 * Get existing sheet or create new one with headers
 */
function getOrCreateSheet() {
  const ss = SpreadsheetApp.openById(SHEET_ID);
  let sheet = ss.getSheetByName(SHEET_NAME);
  
  // Create sheet if it doesn't exist
  if (!sheet) {
    sheet = ss.insertSheet(SHEET_NAME);
    
    // Add headers
    const headers = [
      'Timestamp',
      'Subject ID',
      'Age',
      'Gender',
      'Musical Background',
      'Noise Level',
      'Frequency (Hz)',
      'Pedestal (dBFS)',
      'Duration (ms)',
      'Bitrate (kbps)',
      'Calculated Threshold (dB)',
      'Total Trials',
      'Total Reversals',
      'Raw Trial Data'
    ];
    
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    
    // Format header row
    sheet.getRange(1, 1, 1, headers.length)
      .setBackground('#00d4aa')
      .setFontColor('#ffffff')
      .setFontWeight('bold')
      .setHorizontalAlignment('center');
    
    // Freeze header row
    sheet.setFrozenRows(1);
    
    // Set column widths
    sheet.setColumnWidth(1, 180); // Timestamp
    sheet.setColumnWidth(2, 120); // Subject ID
    sheet.setColumnWidth(11, 150); // Threshold
    sheet.setColumnWidth(14, 300); // Raw Trial Data
  }
  
  return sheet;
}

/**
 * Append data row to sheet
 */
function appendDataToSheet(sheet, data) {
  const row = [
    data.timestamp || new Date().toISOString(),
    data.subjectID || '',
    data.age || '',
    data.gender || '',
    data.musicalBackground || '',
    data.noiseLevel || '',
    data.frequency || '',
    data.pedestal || '',
    data.duration || '',
    data.bitrate || '',
    data.calculatedThreshold_DL || '',
    data.totalTrials || '',
    data.totalReversals || '',
    data.rawTrialData || ''
  ];
  
  sheet.appendRow(row);
  
  // Format the new row
  const lastRow = sheet.getLastRow();
  
  // Alternate row colors for readability
  if (lastRow % 2 === 0) {
    sheet.getRange(lastRow, 1, 1, row.length).setBackground('#f8f9fa');
  }
  
  // Format threshold column as number with 3 decimal places
  if (data.calculatedThreshold_DL) {
    sheet.getRange(lastRow, 11).setNumberFormat('0.000');
  }
}

/**
 * Test function to verify setup
 * Run this from the Apps Script editor to test
 */
function testDataLogging() {
  const testData = {
    timestamp: new Date().toISOString(),
    subjectID: 'TEST_123',
    age: 25,
    gender: 'test',
    musicalBackground: 'some',
    noiseLevel: 'quiet',
    frequency: 1000,
    pedestal: -15,
    duration: 500,
    bitrate: 128,
    calculatedThreshold_DL: 3.456,
    totalTrials: 25,
    totalReversals: 8,
    rawTrialData: '[{"trial":1,"correct":true}]'
  };
  
  const sheet = getOrCreateSheet();
  appendDataToSheet(sheet, testData);
  
  Logger.log('Test data logged successfully!');
  Logger.log('Check your sheet: ' + SpreadsheetApp.openById(SHEET_ID).getUrl());
}

/**
 * Create a summary statistics sheet
 * Run this manually to analyze collected data
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
  
  // Clear existing content
  summarySheet.clear();
  
  // Add summary headers
  summarySheet.getRange('A1').setValue('Summary Statistics');
  summarySheet.getRange('A1').setFontSize(14).setFontWeight('bold');
  
  // Count total participants
  const lastRow = dataSheet.getLastRow();
  summarySheet.getRange('A3').setValue('Total Participants:');
  summarySheet.getRange('B3').setValue(lastRow - 1); // Subtract header row
  
  // Average threshold by frequency
  summarySheet.getRange('A5').setValue('Average Threshold by Frequency');
  summarySheet.getRange('A5').setFontWeight('bold');
  
  const frequencies = [250, 500, 1000, 2000, 3000];
  summarySheet.getRange('A6').setValue('Frequency (Hz)');
  summarySheet.getRange('B6').setValue('Mean Threshold (dB)');
  summarySheet.getRange('C6').setValue('Std Dev');
  summarySheet.getRange('D6').setValue('N');
  
  let row = 7;
  frequencies.forEach(freq => {
    summarySheet.getRange(row, 1).setValue(freq);
    
    // Use AVERAGEIF and STDEV.S formulas
    const avgFormula = `=AVERAGEIF('${SHEET_NAME}'!G:G,${freq},'${SHEET_NAME}'!K:K)`;
    const stdFormula = `=STDEV.S(FILTER('${SHEET_NAME}'!K:K,'${SHEET_NAME}'!G:G=${freq}))`;
    const countFormula = `=COUNTIF('${SHEET_NAME}'!G:G,${freq})`;
    
    summarySheet.getRange(row, 2).setFormula(avgFormula).setNumberFormat('0.000');
    summarySheet.getRange(row, 3).setFormula(stdFormula).setNumberFormat('0.000');
    summarySheet.getRange(row, 4).setFormula(countFormula);
    
    row++;
  });
  
  Logger.log('Summary sheet created!');
}
