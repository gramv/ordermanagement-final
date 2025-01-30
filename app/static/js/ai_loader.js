document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('uploadForm');
    const aiLoaderContainer = document.createElement('div');
    aiLoaderContainer.classList.add('ai-loader-container');
    aiLoaderContainer.innerHTML = `
        <div class="ai-loader">
            <svg class="ai-loader-icon" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
                <circle cx="50" cy="50" r="40" fill="none" stroke="#4a90e2" stroke-width="8"/>
                <path d="M50 10 Q70 30, 50 50 Q30 70, 50 90" fill="none" stroke="#4a90e2" stroke-width="6"/>
                <circle cx="50" cy="50" r="5" fill="#4a90e2">
                    <animateTransform 
                        attributeName="transform" 
                        type="rotate" 
                        from="0 50 50" 
                        to="360 50 50" 
                        dur="2s" 
                        repeatCount="indefinite"/>
                </circle>
            </svg>
            <div class="ai-loader-text">AI Processing Invoice...</div>
        </div>
    `;
    document.body.appendChild(aiLoaderContainer);

    uploadForm.addEventListener('submit', function(e) {
        console.log('Form submitted, showing AI loader');
        aiLoaderContainer.style.display = 'flex';
    });

    // Hide loader on successful response or error
    function hideLoader() {
        console.log('Hiding AI loader');
        aiLoaderContainer.style.display = 'none';
    }

    // Modify fetch to handle loader
    const originalFetch = window.fetch;
    window.fetch = function() {
        const fetchPromise = originalFetch.apply(this, arguments);
        fetchPromise.then(hideLoader).catch(hideLoader);
        return fetchPromise;
    };
});
