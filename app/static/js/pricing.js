// Pricing page JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltips.forEach(tooltip => new bootstrap.Tooltip(tooltip));
    
    // Handle location analysis
    const analyzeBtn = document.getElementById('analyzeLocation');
    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', async function() {
            const location = document.getElementById('location').value;
            const areaType = document.getElementById('areaType').value;
            
            if (!location) {
                showAlert('Please enter a location', 'warning');
                return;
            }
            
            try {
                // Show loading state
                analyzeBtn.disabled = true;
                analyzeBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Analyzing...';
                
                // Make API call
                const response = await fetch(`/invoice/${invoiceId}/analyze-location`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ location, area_type: areaType })
                });
                
                const data = await response.json();
                
                if (!response.ok) {
                    throw new Error(data.error || 'Failed to analyze location');
                }
                
                // Update UI with results
                updateMargins(data.margins);
                updateInsights(data.insights);
                
                // Show insights card
                document.getElementById('insightsCard').classList.remove('d-none');
                
                showAlert('Location analysis complete!', 'success');
                
            } catch (error) {
                showAlert(error.message, 'danger');
            } finally {
                // Reset button state
                analyzeBtn.disabled = false;
                analyzeBtn.innerHTML = '<i class="fas fa-robot me-2"></i>Analyze Location';
            }
        });
    }
    
    // Handle category margin changes
    document.querySelectorAll('.category-margin').forEach(input => {
        input.addEventListener('change', function() {
            const categoryId = this.dataset.categoryId;
            const margin = parseFloat(this.value) || 0;
            
            // Update all products in this category
            document.querySelectorAll(`.product-margin[data-category="${categoryId}"]`)
                .forEach(productInput => {
                    productInput.value = margin;
                    updateProductPrices(productInput);
                });
        });
    });
    
    // Handle individual product margin changes
    document.querySelectorAll('.product-margin').forEach(input => {
        input.addEventListener('change', function() {
            updateProductPrices(this);
        });
    });
    
    // Handle save all
    document.getElementById('saveAll').addEventListener('click', async function() {
        try {
            // Collect all margins
            const margins = {};
            document.querySelectorAll('.category-margin').forEach(input => {
                margins[input.dataset.categoryId] = parseFloat(input.value) || 0;
            });
            
            // Make API call
            const response = await fetch(`/invoice/${invoiceId}/save-prices`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ margins })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Failed to save prices');
            }
            
            showAlert('Prices saved successfully!', 'success');
            
            // Redirect to invoice list after short delay
            setTimeout(() => {
                window.location.href = '/invoice/manage';
            }, 1500);
            
        } catch (error) {
            showAlert(error.message, 'danger');
        }
    });
});

// Helper Functions

function updateMargins(margins) {
    // Update category margins
    for (const [category, margin] of Object.entries(margins)) {
        const input = document.querySelector(`.category-margin[data-category="${category}"]`);
        if (input) {
            input.value = margin;
            // Trigger change event to update products
            input.dispatchEvent(new Event('change'));
        }
    }
}

function updateInsights(insights) {
    // Update demographics
    const demoList = document.getElementById('demographicsInfo');
    demoList.innerHTML = insights.demographics
        .map(insight => `<li><i class="fas fa-check-circle text-success me-2"></i>${insight}</li>`)
        .join('');
    
    // Update competition
    const compList = document.getElementById('competitionInfo');
    compList.innerHTML = insights.competition
        .map(insight => `<li><i class="fas fa-info-circle text-primary me-2"></i>${insight}</li>`)
        .join('');
    
    // Update recommendations
    const recoList = document.getElementById('recommendationsInfo');
    recoList.innerHTML = insights.recommendations
        .map(reco => `<li><i class="fas fa-lightbulb text-warning me-2"></i>${reco}</li>`)
        .join('');
}

function updateProductPrices(input) {
    const row = input.closest('.product-row');
    const costPrice = parseFloat(row.querySelector('.cost-price').textContent);
    const margin = parseFloat(input.value) || 0;
    
    const sellingPrice = costPrice * (1 + margin / 100);
    row.querySelector('.selling-price').textContent = sellingPrice.toFixed(2);
    
    // Update profit
    const profit = sellingPrice - costPrice;
    row.querySelector('.profit').textContent = profit.toFixed(2);
}

function showAlert(message, type) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.querySelector('.container');
    container.insertBefore(alertDiv, container.firstChild);
    
    // Auto dismiss after 5 seconds
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}
