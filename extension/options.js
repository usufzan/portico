// Saves options to chrome.storage
function save_options() {
  const theme = document.getElementById('theme').value;
  const downloadFormat = document.getElementById('downloadFormat').value;
  const autoDetect = document.getElementById('autoDetect').checked;
  const historyLimit = parseInt(document.getElementById('historyLimit').value, 10);
  const analyticsEnabled = document.getElementById('analyticsEnabled').checked;

  chrome.storage.sync.set({
    theme: theme,
    downloadFormat: downloadFormat,
    autoDetect: autoDetect,
    historyLimit: historyLimit,
    analyticsEnabled: analyticsEnabled
  }, function() {
    // Update status to let user know options were saved.
    const status = document.getElementById('status');
    status.textContent = 'Options saved.';
    setTimeout(function() {
      status.textContent = '';
    }, 1500);
  });
}

// Restores select box and checkbox state using the preferences
// stored in chrome.storage.
function restore_options() {
  // Use default values from background.js for initialization
  chrome.storage.sync.get({
    theme: 'light',
    downloadFormat: 'markdown',
    autoDetect: true,
    historyLimit: 10,
    analyticsEnabled: false
  }, function(items) {
    document.getElementById('theme').value = items.theme;
    document.getElementById('downloadFormat').value = items.downloadFormat;
    document.getElementById('autoDetect').checked = items.autoDetect;
    document.getElementById('historyLimit').value = items.historyLimit;
    document.getElementById('analyticsEnabled').checked = items.analyticsEnabled;
  });
}

document.addEventListener('DOMContentLoaded', restore_options);
document.getElementById('save').addEventListener('click', save_options);