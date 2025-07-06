document.addEventListener('DOMContentLoaded', () => {
    // --- Theme Switcher ---
    const themeToggle = document.getElementById('theme-toggle');
    const applyTheme = (theme) => {
        document.body.classList.toggle('dark-theme', theme === 'dark-theme');
        if (themeToggle) themeToggle.checked = (theme === 'dark-theme');
    };
    const savedTheme = localStorage.getItem('theme') || 'light';
    applyTheme(savedTheme);
    themeToggle?.addEventListener('change', () => {
        const newTheme = themeToggle.checked ? 'dark-theme' : 'light';
        localStorage.setItem('theme', newTheme);
        applyTheme(newTheme);
    });

    // --- Core Page Logic ---
    const uploadForm = document.getElementById('upload-form');
    if (uploadForm) {
        const fileInput = document.getElementById('file-input');
        const dropZone = document.querySelector('.file-drop-zone');
        const fileListElem = document.getElementById('file-list');
        const fileListArea = document.getElementById('file-list-area');
        const submitButton = document.getElementById('submit-button');
        const resultArea = document.getElementById('result-area');
        const clearButton = document.getElementById('clear-selection');
        const toolId = uploadForm.querySelector('input[name="tool_id"]').value;

        let currentFiles = [];

        const updateFileListDisplay = () => {
            fileListElem.innerHTML = '';
            if (currentFiles.length === 0) {
                fileListArea.classList.add('hidden');
                submitButton.disabled = true;
                return;
            }

            fileListArea.classList.remove('hidden');
            currentFiles.forEach(file => {
                const li = document.createElement('li');
                li.innerHTML = `<span>${file.name}</span> <span class="file-size">${formatBytes(file.size)}</span>`;
                fileListElem.appendChild(li);
            });
            submitButton.disabled = false;
        };

        const handleNewFiles = (files) => {
            const fileArray = Array.from(files);
            if (toolId === 'pdf-merger') {
                fileArray.forEach(file => {
                    if (!currentFiles.some(f => f.name === file.name && f.size === file.size)) {
                        currentFiles.push(file);
                    }
                });
            } else {
                currentFiles = fileArray.slice(0, 1);
            }
            
            updateFileListDisplay();

            if (toolId === 'split-pdf' && currentFiles.length > 0) {
                initializeSplitter(currentFiles[0]);
            }
        };
        
        fileInput.addEventListener('change', () => handleNewFiles(fileInput.files));
        dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('drag-over'); });
        dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('drag-over');
            handleNewFiles(e.dataTransfer.files);
        });

        clearButton.addEventListener('click', () => {
            currentFiles = [];
            fileInput.value = '';
            updateFileListDisplay();
            resultArea.classList.add('hidden');
            if (toolId === 'split-pdf') {
                document.getElementById('split-tool-options').classList.add('hidden');
            }
        });
        
        const initializeSplitter = (file) => {
            const optionsContainer = document.getElementById('split-tool-options');
            const rangeContainer = document.getElementById('custom-range-container');
            const slider = document.getElementById('page-range-slider');
            const readout = document.getElementById('slider-readout');
            const splitPageInput = document.getElementById('split-page-input');
            const splitRadios = document.querySelectorAll('input[name="split-option"]');

            const fileReader = new FileReader();
            fileReader.onload = function() {
                const typedarray = new Uint8Array(this.result);
                pdfjsLib.getDocument(typedarray).promise.then(pdf => {
                    optionsContainer.classList.remove('hidden');
                    const rangeRadio = document.querySelector('input[value="range"]');
                    if (pdf.numPages < 2) {
                        rangeContainer.classList.add('hidden');
                        if(rangeRadio) rangeRadio.disabled = true;
                        return;
                    }
                    
                    if(rangeRadio) rangeRadio.disabled = false;
                    slider.max = pdf.numPages - 1;
                    slider.value = Math.max(1, Math.floor(pdf.numPages / 2));
                    readout.textContent = `Split at page: ${slider.value}`;
                    splitPageInput.value = slider.value;
                });
            };
            fileReader.readAsArrayBuffer(file);

            splitRadios.forEach(radio => radio.onchange = () => {
                rangeContainer.classList.toggle('hidden', radio.value !== 'range');
            });
            slider.oninput = () => {
                readout.textContent = `Split at page: ${slider.value}`;
                splitPageInput.value = slider.value;
            };
        };

        // --- Form Submission with Progress Bar ---
        uploadForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            // Show progress bar
            resultArea.classList.remove('hidden');
            resultArea.innerHTML = `
                <div class="progress-container">
                    <p>Processing your file...</p>
                    <div class="progress-bar-background">
                        <div id="progress-bar" class="progress-bar"></div>
                    </div>
                </div>`;
            
            // --- THIS IS THE CHANGE ---
            // Immediately scroll down to show the user the process has started
            resultArea.scrollIntoView({ behavior: 'smooth', block: 'center' });
            
            const progressBar = document.getElementById('progress-bar');
            setTimeout(() => { progressBar.style.width = '95%'; }, 100);

            submitButton.disabled = true;

            const formData = new FormData();
            formData.append('tool_id', toolId);
            currentFiles.forEach(file => {
                formData.append('files[]', file);
            });
            
            if (toolId === 'split-pdf') {
                const checkedOption = document.querySelector('input[name="split-option"]:checked');
                if (checkedOption) {
                    formData.append('split-option', checkedOption.value);
                    if (checkedOption.value === 'range') {
                        formData.append('split_page', document.getElementById('split-page-input').value);
                    }
                }
            }

            try {
                const response = await fetch('/upload', { method: 'POST', body: formData });
                const result = await response.json();

                progressBar.classList.add('finished');
                progressBar.style.width = '100%';

                // Display the final result after a short delay
                setTimeout(() => {
                    if (result.status === 'success') {
                        resultArea.innerHTML = `<div class="message success"><p>${result.message}</p><a href="${result.download_url}" class="download-button">Download Result</a></div>`;
                    } else {
                        resultArea.innerHTML = `<div class="message error"><p>${result.message || 'An unknown error occurred.'}</p></div>`;
                    }
                }, 500);

            } catch (error) {
                // Display error message
                 setTimeout(() => {
                    resultArea.innerHTML = `<div class="message error"><p>A network error occurred. Please try again.</p></div>`;
                }, 500);
            } finally {
                submitButton.disabled = false;
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
