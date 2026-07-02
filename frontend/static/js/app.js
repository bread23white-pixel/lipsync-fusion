// File inputs
const mediaInput = document.getElementById('media-input');
const audioInput = document.getElementById('audio-input');
const mediaName = document.getElementById('media-name');
const audioName = document.getElementById('audio-name');
const generateBtn = document.getElementById('generate-btn');
const progressContainer = document.getElementById('progress-container');
const progressFill = document.getElementById('progress-fill');
const progressText = document.getElementById('progress-text');
const resultsSection = document.getElementById('results-section');
const previewVideo = document.getElementById('preview-video');
const downloadBtn = document.getElementById('download-btn');

let currentJobId = null;

// File upload handlers
mediaInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        mediaName.textContent = `✓ ${file.name}`;
        checkFilesReady();
    }
});

audioInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        audioName.textContent = `✓ ${file.name}`;
        checkFilesReady();
    }
});

// Check if both files are selected
function checkFilesReady() {
    if (mediaInput.files.length > 0 && audioInput.files.length > 0) {
        generateBtn.disabled = false;
    }
}

// Motion intensity slider
const motionSlider = document.getElementById('motion-slider');
const motionValue = document.getElementById('motion-value');

motionSlider.addEventListener('input', (e) => {
    motionValue.textContent = `${e.target.value}%`;
});

// Generate button
generateBtn.addEventListener('click', async () => {
    generateBtn.disabled = true;
    
    try {
        // Step 1: Upload files
        const formData = new FormData();
        formData.append('media', mediaInput.files[0]);
        formData.append('audio', audioInput.files[0]);
        
        progressContainer.style.display = 'block';
        progressText.textContent = 'Uploading files...';
        progressFill.style.width = '20%';
        
        const uploadResponse = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        if (!uploadResponse.ok) {
            throw new Error('Upload failed');
        }
        
        const uploadData = await uploadResponse.json();
        currentJobId = uploadData.job_id;
        
        // Step 2: Generate
        progressText.textContent = 'Generating lip-sync...';
        progressFill.style.width = '50%';
        
        const generateResponse = await fetch('/api/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                job_id: currentJobId,
                model: document.getElementById('model-select').value,
                emotion: document.getElementById('emotion-select').value,
                motion_intensity: parseInt(motionSlider.value) / 100,
                accuracy_mode: document.getElementById('accuracy-select').value
            })
        });
        
        if (!generateResponse.ok) {
            throw new Error('Generation failed');
        }
        
        const generateData = await generateResponse.json();
        
        // Step 3: Display results
        progressFill.style.width = '100%';
        progressText.textContent = 'Complete!';
        
        // Show results after a short delay
        setTimeout(() => {
            progressContainer.style.display = 'none';
            resultsSection.style.display = 'block';
            previewVideo.src = generateData.output_path;
        }, 500);
    } 
    catch (error) {
        progressText.textContent = `Error: ${error.message}`;
        progressText.style.color = '#f56565';
    } 
    finally {
        generateBtn.disabled = false;
    }
});

// Download button
downloadBtn.addEventListener('click', () => {
    if (currentJobId) {
        window.location.href = `/api/download/${currentJobId}`;
    }
});

console.log('LipSync Fusion loaded');
