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

  // Connection Badge Elements
  const engineStatus = document.getElementById('engine-status');
  const engineStatusText = document.getElementById('engine-status-text');

  // Connection Settings Elements
  const toggleSettingsBtn = document.getElementById('toggle-settings-btn');
  const settingsPanel = document.getElementById('settings-panel');
  const backendUrlInput = document.getElementById('backend-url');
  const securityTokenInput = document.getElementById('security-token');
  const saveSettingsBtn = document.getElementById('save-settings-btn');

  // Resolve or load backend Base URL
  let backendBaseUrl = localStorage.getItem('teledown_backend_url');
  if (!backendBaseUrl) {
    const currentHostname = window.location.hostname;
    const currentProtocol = window.location.protocol;
    
    if (window.location.port) {
      backendBaseUrl = `${currentProtocol}//${currentHostname}:${window.location.port}`;
    } else if (currentHostname.includes('pinggy') || currentHostname.includes('ngrok')) {
      backendBaseUrl = `${currentProtocol}//${currentHostname}`;
    } else {
      backendBaseUrl = 'http://localhost:8000';
    }
  }
  backendUrlInput.value = backendBaseUrl;

  // Load security token
  let securityToken = localStorage.getItem('teledown_security_token') || '';
  securityTokenInput.value = securityToken;

  // Settings Panel Toggle
  toggleSettingsBtn.addEventListener('click', () => {
    settingsPanel.classList.toggle('hidden');
  });

  // Settings Save
  saveSettingsBtn.addEventListener('click', () => {
    let url = backendUrlInput.value.trim();
    if (!url) {
      alert('Please enter a valid backend URL.');
      return;
    }
    if (url.endsWith('/')) {
      url = url.slice(0, -1);
    }
    backendBaseUrl = url;
    localStorage.setItem('teledown_backend_url', url);

    securityToken = securityTokenInput.value.trim();
    localStorage.setItem('teledown_security_token', securityToken);

    settingsPanel.classList.add('hidden');
    checkEngineHealth(); // Trigger immediate check
  });

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

  // Helper: Update engine connection badge
  function updateEngineStatus(online) {
    const dot = engineStatus.querySelector('span');
    if (online) {
      engineStatus.className = 'text-xs font-semibold px-3 py-1.5 rounded-full flex items-center gap-1.5 bg-emerald-950/30 border border-emerald-800/30 text-emerald-400 select-none transition-all duration-300';
      dot.className = 'h-2 w-2 rounded-full bg-emerald-500';
      engineStatusText.textContent = 'Local Engine Connected';
    } else {
      engineStatus.className = 'text-xs font-semibold px-3 py-1.5 rounded-full flex items-center gap-1.5 bg-red-950/30 border border-red-800/30 text-red-400 select-none transition-all duration-300';
      dot.className = 'h-2 w-2 rounded-full bg-red-500';
      engineStatusText.textContent = 'Local Engine Offline - Run start script';
    }
  }

  // Check backend server health endpoint
  async function checkEngineHealth() {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 2000); // 2 second timeout

      const headers = {};
      if (securityToken) {
        headers['Authorization'] = `Bearer ${securityToken}`;
      }

      const response = await fetch(`${backendBaseUrl}/health`, {
        signal: controller.signal,
        mode: 'cors',
        headers: headers
      });

      clearTimeout(timeoutId);

      if (response.ok) {
        const data = await response.json();
        if (data.status === 'online') {
          updateEngineStatus(true);
          return;
        }
      }
      updateEngineStatus(false);
    } catch (_) {
      updateEngineStatus(false);
    }
  }

  // Initial and periodic checks
  checkEngineHealth();
  setInterval(checkEngineHealth, 10000);

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
      let streamUrl = `${backendBaseUrl}/stream?link=${encodeURIComponent(link)}`;
      if (securityToken) {
        streamUrl += `&token=${encodeURIComponent(securityToken)}`;
      }

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
