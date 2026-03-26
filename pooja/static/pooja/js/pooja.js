// Pooja Name Validation
function validatePoojaName(name) {
    // Allow letters, spaces, hyphens, apostrophes, and periods
    // Minimum 3 characters, maximum 200 (matching model)
    const regex = /^[a-zA-Z\s\-'.]{3,200}$/;
    return regex.test(name);
}

// Additional JavaScript validation
const poojaForm = document.getElementById('poojaForm');
if (poojaForm) {
    const nameInput = poojaForm.querySelector('input[name="name"]');
    const errorDiv = document.createElement('div');
    errorDiv.className = 'text-red-600 text-sm mt-1 hidden';
    nameInput.parentNode.insertBefore(errorDiv, nameInput.nextSibling);

    // Real-time validation
    nameInput.addEventListener('input', function() {
        const name = this.value.trim();
        if (name.length > 0 && !validatePoojaName(name)) {
            errorDiv.textContent = 'Pooja name can only contain letters, spaces, hyphens (-), apostrophes (\'), and periods (.). Minimum 3 characters.';
            errorDiv.classList.remove('hidden');
            this.classList.add('border-red-500');
        } else {
            errorDiv.classList.add('hidden');
            this.classList.remove('border-red-500');
        }
    });

    // Form submission validation
    poojaForm.addEventListener('submit', function(e) {
        const name = nameInput.value.trim();
        const dateInput = document.getElementById('pooja_date');
        
        // Validate pooja name
        if (!validatePoojaName(name)) {
            e.preventDefault();
            errorDiv.textContent = 'Please enter a valid pooja name (letters, spaces, hyphens, apostrophes, and periods only).';
            errorDiv.classList.remove('hidden');
            nameInput.focus();
            nameInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
            return;
        }
        
        // Validate date if provided
        if (dateInput && dateInput.value) {
            const selectedDate = new Date(dateInput.value);
            const today = new Date();
            today.setHours(0, 0, 0, 0);

            if (selectedDate < today) {
                e.preventDefault();
                alert('Pooja date cannot be in the past. Please select today or a future date.');
                dateInput.focus();
            }
        }
    });
}


// Update minimum date dynamically (in case user keeps form open overnight)
setInterval(function() {
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('pooja_date').setAttribute('min', today);
        }, 60000); 


// pooja search
// pooja search (runs ONLY if search elements exist)
document.addEventListener("DOMContentLoaded", () => {
    
    const searchForm = document.getElementById("pooja-search-form");
    const searchInput = document.getElementById("search-input");
    const cards = document.querySelectorAll(".card-parent");

    if (!searchForm || !searchInput) return;

    searchForm.addEventListener("submit", function(e) {
        e.preventDefault();

        const q = searchInput.value.trim().toLowerCase();
        if (q === "") {
            // show all cards again
            cards.forEach(card => card.style.display = "block");
            return;
        }

        let found = false;

        cards.forEach(card => {
            const name = card.dataset.name; // p.name from Django

            if (name.includes(q)) {
                card.style.display = "block";
                found = true;
            } else {
                card.style.display = "none";
            }
        });

        // OPTIONAL: Show a message if no results found
        const noMsg = document.getElementById("search-results");
        if (found) {
            noMsg.innerHTML = "";
        } else {
            noMsg.innerHTML = `<span class="text-red-600">No matching poojas found.</span>`;
        }
    });
});