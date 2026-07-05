document.addEventListener('DOMContentLoaded', () => {
  const telegramLinkInput = document.getElementById('telegram-link');
  const downloadBtn = document.getElementById('download-btn');
  const btnText = document.getElementById('btn-text');
  const btnIcon = document.getElementById('btn-icon');
  const btnSpinner = document.getElementById('btn-spinner');
  const errorBanner = document.getElementById('error-banner');
  const errorMessage = document.getElementById('error-message');
  const progressContainer = document.getElementById('progress-container');
  const statusText = document.getElementById('status-text');
  const percentageLabel = document.getElementById('percentage-label');
  const progressIndicator = document.getElementById('progress-indicator');
  const downloadedLabel = document.getElementById('downloaded-label');
  const totalLabel = document.getElementById('total-label');

  // Helper: Display error message
  function showError(msg) {
    errorMessage.textContent = msg;
    errorBanner.classList.remove('hidden');
    progressContainer.classList.add('hidden');
  }

  // Helper: Clear error message
  function clearError() {
    errorBanner.classList.add('hidden');
    errorMessage.textContent = '';
  }

  // Main download trigger
  downloadBtn.addEventListener('click', () => {
    clearError();
    const link = telegramLinkInput.value.trim();

    if (!link) {
      showError('Please enter a valid Telegram link.');
      return;
    }

    if (!link.startsWith('http://') && !link.startsWith('https://')) {
      showError('Invalid link format. Must start with http:// or https://');
      return;
    }

    try {
      // Build the backend stream endpoint URL
      const streamUrl = `http://localhost:8000/stream?link=${encodeURIComponent(link)}`;

      // Update button state to success
      btnIcon.className = 'fa-solid fa-circle-check';
      btnText.textContent = 'Streaming Started!';
      downloadBtn.classList.remove('from-blue-600', 'to-indigo-600', 'hover:from-blue-500', 'hover:to-indigo-500');
      downloadBtn.classList.add('from-emerald-600', 'to-teal-650', 'hover:from-emerald-500', 'hover:to-teal-550');

      // Update the progress container to guide the user to check native downloads
      progressContainer.classList.remove('hidden');
      statusText.textContent = 'Piping stream to browser...';
      percentageLabel.textContent = 'Active';
      progressIndicator.style.width = '100%';
      progressIndicator.classList.remove('from-blue-500', 'via-indigo-500', 'to-purple-500');
      progressIndicator.classList.add('from-emerald-500', 'via-teal-500', 'to-green-500');
      
      downloadedLabel.textContent = 'Check browser downloads';
      totalLabel.textContent = '(Ctrl+J / Cmd+Option+L)';

      // Trigger direct native browser download stream by changing location
      // This has zero JS memory overhead since the browser handles chunk-by-chunk writing
      window.location.href = streamUrl;

      // Re-enable button after 5 seconds so they can download another file if desired
      setTimeout(() => {
        btnIcon.className = 'fa-solid fa-cloud-arrow-down';
        btnText.textContent = 'Stream Download';
        downloadBtn.classList.add('from-blue-600', 'to-indigo-600', 'hover:from-blue-500', 'hover:to-indigo-500');
        downloadBtn.classList.remove('from-emerald-600', 'to-teal-650', 'hover:from-emerald-500', 'hover:to-teal-550');
      }, 5000);

    } catch (error) {
      console.error('Redirection error:', error);
      showError('Failed to initiate native stream redirect.');
    }
  });
});
