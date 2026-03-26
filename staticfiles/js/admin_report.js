const apiUrl = "/api/admin/reports/bookings/";
let typingTimer;
const TYPING_DELAY = 300; // ms

function buildQuery(exportCsv = false) {
    const params = new URLSearchParams();

    const singleDate = singleDateEl.value;
    const fromDate = fromDateEl.value;
    const toDate = toDateEl.value;
    const search = searchInputEl.value.trim();
    const paymentStatus = paymentStatusEl.value;
    const bookingStatus = bookingStatusEl.value;
    const paymentMethod = paymentMethodEl.value;

    if (singleDate) params.append("date", singleDate);
    if (fromDate && toDate) {
        params.append("from", fromDate);
        params.append("to", toDate);
    }
    if (search) params.append("search", search);
    if (paymentStatus) params.append("payment_status", paymentStatus);
    if (bookingStatus) params.append("booking_status", bookingStatus);
    if (paymentMethod) params.append("payment_method", paymentMethod);
    if (exportCsv) params.append("export", "csv");

    return params.toString();
}

async function fetchReport() {
    const res = await fetch(`${apiUrl}?${buildQuery()}`);
    const data = await res.json();

    // SUMMARY
    totalBookingsEl.innerText = data.summary.total_bookings;
    totalRevenueEl.innerText = "₹" + data.summary.total_revenue;

    // Get unique payment methods
    const uniquePaymentMethods = [];
    const seenMethods = new Set();
    
    if (data.grouped_by_payment_method && data.grouped_by_payment_method.length) {
        data.grouped_by_payment_method.forEach(p => {
            if (p.payment_method && !seenMethods.has(p.payment_method)) {
                seenMethods.add(p.payment_method);
                uniquePaymentMethods.push(p.payment_method);
            }
        });
    }
    
    paymentModesEl.textContent = uniquePaymentMethods.length ? uniquePaymentMethods.join(", ") : "—";

    // TABLE
    reportTableBody.innerHTML = "";

    if (!data.bookings.length) {
        reportTableBody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center py-4 text-gray-500">
                    No bookings found
                </td>
            </tr>
        `;
        return;
    }

    data.bookings.forEach(b => {
        reportTableBody.innerHTML += `
            <tr>
                <td class="border px-2 py-2">${b.booking_id}</td>
                <td class="border px-2 py-2">${b.pooja_name}</td>
                <td class="border px-2 py-2">${b.devotee_name}</td>
                <td class="border px-2 py-2">${b.pooja_date}</td>
                <td class="border px-2 py-2">₹${b.amount}</td>
                <td class="border px-2 py-2">${b.payment_method}</td>
                <td class="border px-2 py-2">${b.booking_status}</td>
            </tr>
        `;
    });
}

/* =======================
   ELEMENT REFERENCES
======================= */
const singleDateEl = document.getElementById("singleDate");
const fromDateEl = document.getElementById("fromDate");
const toDateEl = document.getElementById("toDate");
const searchInputEl = document.getElementById("searchInput");
const paymentStatusEl = document.getElementById("paymentStatus");
const bookingStatusEl = document.getElementById("bookingStatus");
const paymentMethodEl = document.getElementById("paymentMethod");

const totalBookingsEl = document.getElementById("totalBookings");
const totalRevenueEl = document.getElementById("totalRevenue");
const paymentModesEl = document.getElementById("paymentModes");
const reportTableBody = document.getElementById("reportTableBody");

/* =======================
   AUTO-FETCH EVENTS
======================= */

// Instant fetch for selects & dates
[
    singleDateEl,
    fromDateEl,
    toDateEl,
    paymentStatusEl,
    bookingStatusEl,
    paymentMethodEl
].forEach(el => {
    el.addEventListener("change", fetchReport);
});

// Debounced fetch for search input
searchInputEl.addEventListener("keyup", () => {
    clearTimeout(typingTimer);
    typingTimer = setTimeout(fetchReport, TYPING_DELAY);
});

/* =======================
   CSV EXPORT
======================= */
document.getElementById("csvBtn").addEventListener("click", exportToCsv);

async function exportToCsv() {
    try {
        // Build the query with export=csv parameter
        const queryString = buildQuery(true);
        
        // Open the URL directly in a new tab/window
        window.open(`/api/admin/reports/bookings/?${queryString}`, '_blank');
    } catch (error) {
        console.error('Error exporting CSV:', error);
        alert('Error exporting CSV. Please try again.');
    }
}
