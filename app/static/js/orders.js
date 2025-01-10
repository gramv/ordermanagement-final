function addToOrderList(productId, quantity, updateQuantity = false) {
    $.ajax({
        url: '/add_to_order_list',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            product_id: productId,
            quantity: quantity,
            order_type: 'daily',  // or get from form
            update_quantity: updateQuantity
        }),
        success: function(response) {
            if (response.status === 'exists') {
                // Product exists - ask for confirmation
                if (confirm(response.message)) {
                    // User confirmed - update quantity
                    addToOrderList(productId, quantity, true);
                } else {
                    // User cancelled - clear form
                    clearOrderForm();
                }
            } else if (response.success) {
                // Show success message
                showToast('Success', response.message, 'success');
                clearOrderForm();
            } else {
                // Show error message
                showToast('Error', response.message, 'error');
            }
        },
        error: function(xhr) {
            let errorMessage = 'An error occurred';
            try {
                errorMessage = JSON.parse(xhr.responseText).message;
            } catch (e) {
                console.error('Error parsing response:', e);
            }
            showToast('Error', errorMessage, 'error');
        }
    });
}

function clearOrderForm() {
    $('#product-search').val('');
    $('#product-id').val('');
    $('#quantity').val('');
    $('#search-results').hide();
}

function showToast(title, message, type) {
    // Using Bootstrap Toast
    const toast = `
        <div class="toast" role="alert" aria-live="assertive" aria-atomic="true" data-delay="3000">
            <div class="toast-header bg-${type === 'success' ? 'success' : 'danger'} text-white">
                <strong class="mr-auto">${title}</strong>
                <button type="button" class="ml-2 mb-1 close" data-dismiss="toast" aria-label="Close">
                    <span aria-hidden="true">&times;</span>
                </button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;
    
    $('#toast-container').append(toast);
    $('.toast').toast('show');
} 