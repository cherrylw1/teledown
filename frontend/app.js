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
    setLoading(false);
  }

  // Helper: Clear error message
  function clearError() {
    errorBanner.classList.add('hidden');
    errorMessage.textContent = '';
  }

  // Helper: Toggle loading state on button
  function setLoading(isLoading) {
    if (isLoading) {
      downloadBtn.disabled = true;
      downloadBtn.classList.add('opacity-80', 'cursor-not-allowed');
      btnIcon.classList.add('hidden');
      btnSpinner.classList.remove('hidden');
      btnText.textContent = 'Streaming File...';
    } else {
      downloadBtn.disabled = false;
      downloadBtn.classList.remove('opacity-80', 'cursor-not-allowed');
      btnIcon.classList.remove('hidden');
      btnSpinner.classList.add('hidden');
      btnText.textContent = 'Stream Download';
    }
  }

  // Helper: Format bytes to MB
  function formatMB(bytes) {
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
  }

  // Helper: Guess file extension from mime type
  function getExtensionFromMime(mimeType) {
    const map = {
      'video/mp4': 'mp4',
      'video/x-matroska': 'mkv',
      'video/quicktime': 'mov',
      'audio/mpeg': 'mp3',
      'audio/ogg': 'ogg',
      'image/jpeg': 'jpg',
      'image/png': 'png',
      'application/pdf': 'pdf',
      'application/zip': 'zip',
      'application/x-tar': 'tar',
      'text/plain': 'txt'
    };
    return map[mimeType] || 'bin';
  }

  // Helper: Parse filename from Content-Disposition header
  function parseFilename(disposition, mimeType) {
    let filename = 'telegram_file';
    if (disposition) {
      // Look for filename*="utf-8''filename.ext" or filename="filename.ext"
      const filenameStarRegex = /filename\*=utf-8''([^;\n]+)/i;
      const filenameRegex = /filename="?([^;\n"]+)"?/i;
      
      let matches = filenameStarRegex.exec(disposition);
      if (matches && matches[1]) {
        filename = decodeURIComponent(matches[1]);
      } else {
        matches = filenameRegex.exec(disposition);
        if (matches && matches[1]) {
          filename = matches[1];
        }
      }
    } else if (mimeType) {
      filename += '.' + getExtensionFromMime(mimeType);
    }
    return filename;
  }

  // Main download trigger
  downloadBtn.addEventListener('click', async () => {
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

    setLoading(true);
    progressContainer.classList.remove('hidden');
    statusText.textContent = 'Connecting to stream server...';
    progressIndicator.style.width = '0%';
    percentageLabel.textContent = '0%';
    downloadedLabel.textContent = '0.00 MB';
    totalLabel.textContent = 'Calculating size...';

    try {
      const backendUrl = `http://localhost:8000/stream?link=${encodeURIComponent(link)}`;
      const response = await fetch(backendUrl);

      if (!response.ok) {
        let errorDetails = `HTTP status ${response.status}`;
        try {
          const errData = await response.json();
          if (errData && errData.detail) {
            errorDetails = errData.detail;
          }
        } catch (_) {
          // Fall back to plain text if JSON parsing fails
          const text = await response.text();
          if (text) errorDetails = text.substring(0, 100);
        }
        throw new Error(errorDetails);
      }

      if (!response.body) {
        throw new Error('ReadableStream not supported by backend response.');
      }

      statusText.textContent = 'Streaming file data...';

      // Parse headers
      const contentLengthHeader = response.headers.get('Content-Length');
      const contentDispositionHeader = response.headers.get('Content-Disposition');
      const contentTypeHeader = response.headers.get('Content-Type');

      const totalBytes = contentLengthHeader ? parseInt(contentLengthHeader, 10) : null;
      const filename = parseFilename(contentDispositionHeader, contentTypeHeader);

      if (totalBytes) {
        totalLabel.textContent = `of ${formatMB(totalBytes)}`;
      } else {
        totalLabel.textContent = 'Dynamic Stream (Unknown size)';
      }

      // Read the stream
      const reader = response.body.getReader();
      const chunks = [];
      let receivedBytes = 0;

      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          break;
        }

        chunks.push(value);
        receivedBytes += value.length;

        // Update progress bar
        downloadedLabel.textContent = formatMB(receivedBytes);

        if (totalBytes) {
          const percent = Math.min(100, Math.round((receivedBytes / totalBytes) * 100));
          progressIndicator.style.width = `${percent}%`;
          percentageLabel.textContent = `${percent}%`;
          statusText.textContent = `Streaming... (${formatMB(receivedBytes)} downloaded)`;
        } else {
          // Dynamic counter without Content-Length
          progressIndicator.style.width = '100%';
          percentageLabel.textContent = 'N/A';
          statusText.textContent = `Streaming dynamically... (${formatMB(receivedBytes)} downloaded)`;
        }
      }

      statusText.textContent = 'Finalizing download...';
      
      // Compile chunks into a single Blob and trigger browser download
      const blob = new Blob(chunks, { type: contentTypeHeader || 'application/octet-stream' });
      const objectUrl = URL.createObjectURL(blob);

      const downloadAnchor = document.createElement('a');
      downloadAnchor.href = objectUrl;
      downloadAnchor.download = filename;
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      
      // Clean up
      downloadAnchor.remove();
      URL.revokeObjectURL(objectUrl);

      statusText.textContent = 'Download completed successfully!';
      setLoading(false);

    } catch (error) {
      console.error('Download stream error:', error);
      showError(error.message || 'An unexpected error occurred while streaming.');
    }
  });
});
