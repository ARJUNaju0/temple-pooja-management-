console.log('cancel_booking.js loaded');

// Wait for the DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM fully loaded, initializing cancel booking modal');
    
    // Handle cancel booking modal
    function showCancelModal(url, paymentStatus) {
        console.log('showCancelModal called with:', { url, paymentStatus });
        const modal = document.getElementById('cancelBookingModal');
        const form = document.getElementById('cancelBookingForm');
        const message = document.getElementById('cancelMessage');
        
        if (!modal || !form || !message) {
            console.error('Required elements not found in the DOM');
            return;
        }
        
        // Set the form action
        form.action = url;
        
        // Update the message based on payment status
        let messageText = 'Are you sure you want to cancel this booking?';
        if (paymentStatus === 'completed') {
            messageText += ' A refund will be processed.';
        }
        message.textContent = messageText;
        
        // Show the modal
        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
        
        // Close modal when clicking cancel
        const cancelButton = document.getElementById('cancelBookingCancel');
        if (cancelButton) {
            // Remove any existing event listeners to prevent duplicates
            const newCancelButton = cancelButton.cloneNode(true);
            cancelButton.parentNode.replaceChild(newCancelButton, cancelButton);
            newCancelButton.addEventListener('click', function() {
                modal.classList.add('hidden');
                document.body.style.overflow = '';
            });
        }
        
        // Close modal when clicking outside
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                this.classList.add('hidden');
                document.body.style.overflow = '';
            }
        });
        
        // Close with Escape key
        const handleEscape = function(e) {
            if (e.key === 'Escape' && !modal.classList.contains('hidden')) {
                modal.classList.add('hidden');
                document.body.style.overflow = '';
            }
        };
        
        // Add event listener for Escape key
        document.addEventListener('keydown', handleEscape);
        
        // Cleanup function to remove event listeners
        return function cleanup() {
            document.removeEventListener('keydown', handleEscape);
        };
    }
    
    // Make the function globally available
    window.showCancelModal = showCancelModal;
    console.log('showCancelModal function registered globally');
});
