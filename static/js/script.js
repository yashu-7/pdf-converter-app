// static/js/script.js (FIXED & IMPROVED)

document.addEventListener('DOMContentLoaded', () => {
    // --- Theme Switcher ---
    const themeToggle = document.getElementById('theme-toggle');
    const applyTheme = (theme) => {
        if (theme === 'dark-theme') {
            document.body.classList.add('dark-theme');
            themeToggle.checked = true;
        } else {
            document.body.classList.remove('dark-theme');
            themeToggle.checked = false;
        }
    };
    const savedTheme = localStorage.getItem('theme') || 'light';
    applyTheme(savedTheme);
    themeToggle.addEventListener('change', () => {
        const newTheme = themeToggle.checked ? 'dark-theme' : 'light';
        localStorage.setItem('theme', newTheme);
        applyTheme(newTheme);
    });

    // --- File Upload Page Logic ---
    const uploadForm = document.getElementById('upload-form');
    if (uploadForm) {
        const fileInput = document.getElementById('file-input');
        const dropZone = document.querySelector('.file-drop-zone');
        const fileListElem = document.getElementById('file-list');
        const submitButton = document.getElementById('submit-button');
        const resultArea = document.getElementById('result-area');
        const statusMessage = document.getElementById('status-message');

        const handleFiles = (files) => {
            fileListElem.innerHTML = '';
            if (files.length === 0) {
                submitButton.disabled = true;
                return;
            }
            // Update the file input's files property for form submission
            fileInput.files = files; 
            
            for (const file of files) {
                const li = document.createElement('li');
                const fileName = document.createElement('span');
                const fileSize = document.createElement('span');
                fileName.textContent = file.name;
                fileSize.textContent = formatBytes(file.size);
                fileSize.className = 'file-size';
                li.appendChild(fileName);
                li.appendChild(fileSize);
                fileListElem.appendChild(li);
            }
            submitButton.disabled = false;
        };

        // Handle clicks and file selection
        fileInput.addEventListener('change', () => handleFiles(fileInput.files));

        // Handle Drag and Drop
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('drag-over');
        });
        dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('drag-over');
            handleFiles(e.dataTransfer.files);
        });

        // Handle Form Submission
        uploadForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            resultArea.classList.remove('hidden');
            statusMessage.innerHTML = '<div class="spinner"></div><p>Processing your files...</p>';
            submitButton.disabled = true;

            const formData = new FormData(uploadForm);
            
            try {
                const response = await fetch('/upload', { method: 'POST', body: formData });
                const result = await response.json();

                if (result.status === 'success') {
                    statusMessage.innerHTML = `
                        <div class="message success">${result.message}</div>
                        <a href="${result.download_url}" class="button-link">Download Result</a>`;
                } else {
                    statusMessage.innerHTML = `<div class="message error">${result.message || 'An unknown error occurred.'}</div>`;
                }
            } catch (error) {
                statusMessage.innerHTML = `<div class="message error">A network error occurred. Please try again.</div>`;
            } finally {
                submitButton.disabled = false;
            }
        });
    }

    // --- Feedback Form ---
    const feedbackForm = document.getElementById('feedback-form');
    if (feedbackForm) {
        feedbackForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const statusDiv = document.getElementById('feedback-status');
            statusDiv.textContent = "Sending...";
            
            try {
                await fetch(feedbackForm.action, {
                    method: 'POST', body: new FormData(feedbackForm), headers: { 'Accept': 'application/json' }
                });
                statusDiv.textContent = "✅ Thanks for your feedback!";
                feedbackForm.reset();
            } catch (error) {
                statusDiv.textContent = "❌ Oops! Something went wrong.";
            }
        });
    }
});

function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}
