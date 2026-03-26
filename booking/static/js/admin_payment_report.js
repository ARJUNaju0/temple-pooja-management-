let chartInstance = null;
const fromDate = document.getElementById("fromDate");
const toDate = document.getElementById("toDate");
const chartTypeSelect = document.getElementById("chartType");
const chartCanvas = document.getElementById('paymentChart');

// Set default to date to today if not set
if (!toDate.value) {
    toDate.value = new Date().toISOString().split('T')[0];
}

[fromDate, toDate, chartTypeSelect].forEach(el =>
    el.addEventListener("change", fetchReport)
);

async function fetchReport() {
    const from = fromDate.value;
    const to = toDate.value || new Date().toISOString().split('T')[0]; // Default to today if to date not set

    const res = await fetch(`/api/admin/payment-report/?from=${from}&to=${to}`);
    if (!res.ok) return;

    const data = await res.json();
    renderSummary(data.summary);
    renderTable(data.breakdown, data.summary.grand_total);
    renderChart(data.breakdown);
}

function renderSummary(s) {
  document.getElementById("summaryCards").classList.remove("hidden");
  cashTotal.innerText = s.cash_total;
  upiTotal.innerText = s.upi_total;
  grandTotal.innerText = s.grand_total;
}

function renderTable(rows, total) {
  const tbody = document.getElementById("reportTable");
  tbody.innerHTML = "";

  if (!rows.length) {
    tbody.innerHTML = `<tr><td colspan="4" class="text-center py-4">No data</td></tr>`;
    return;
  }

  rows.forEach(r => {
    const percent = total ? ((r.total_amount / total) * 100).toFixed(2) : 0;
    tbody.innerHTML += `
      <tr>
        <td class="border px-4 py-2">${r.payment_method.toUpperCase()}</td>
        <td class="border px-4 py-2">${r.booking_count}</td>
        <td class="border px-4 py-2">₹${r.total_amount}</td>
        <td class="border px-4 py-2">${percent}%</td>
      </tr>
    `;
  });
}

function renderChart(rows) {
    const labels = rows.map(r => r.payment_method.toUpperCase());
    const values = rows.map(r => r.total_amount);

    if (chartInstance) {
        chartInstance.destroy();
    }

    // Ensure canvas has proper dimensions
    chartCanvas.style.width = '100%';
    chartCanvas.style.height = '400px';

    chartInstance = new Chart(chartCanvas, {
        type: chartTypeSelect.value,
        data: {
            labels,
            datasets: [{
                data: values,
                backgroundColor: ["#16a34a", "#2563eb"]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                }
            }
        }
    });
}

// CSV
document.getElementById("downloadCsvBtn").onclick = () => {
  const from = fromDate.value;
  const to = toDate.value;
  window.location.href = `/api/admin/payment-report/csv/?from=${from}&to=${to}`;
};

// Initial load
document.addEventListener('DOMContentLoaded', () => {
    fetchReport();
});

// Auto-refresh every 60s (optional)
setInterval(fetchReport, 60000);
