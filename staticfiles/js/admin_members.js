let currentPage = 1;
let totalPages = 1;

const table = document.getElementById("memberTable");
const searchInput = document.getElementById("searchInput");
const pageInfo = document.getElementById("pageInfo");

function loadMembers() {
    table.innerHTML = `
        <tr>
            <td colspan="7" class="text-center py-6 text-gray-500">
                Loading...
            </td>
        </tr>
    `;

    fetch(`/api/admin/members/?search=${searchInput.value}&page=${currentPage}`)
        .then(res => res.json())
        .then(data => {
            totalPages = data.total_pages;
            pageInfo.textContent =
                `Page ${data.page} of ${data.total_pages} — Total ${data.total_members} members`;

            if (!data.results.length) {
                table.innerHTML = `
                    <tr>
                        <td colspan="7" class="text-center py-6 text-gray-500">
                            No members found
                        </td>
                    </tr>
                `;
                return;
            }

            table.innerHTML = "";
            data.results.forEach(m => {
                table.innerHTML += `
                    <tr class="hover:bg-gray-50 cursor-pointer" onclick="window.location='/admin/members/${m.id}/'">
                        <td class="border px-3 py-2">${m.id}</td>
                        <td class="border px-3 py-2 font-semibold">${m.name}</td>
                        <td class="border px-3 py-2">${m.username}</td>
                        <td class="border px-3 py-2">${m.email || "-"}</td>
                        <td class="border px-3 py-2">${m.phone || "-"}</td>
                        <td class="border px-3 py-2">${m.date_joined}</td>
                        <td class="border px-3 py-2">
                            ${m.is_active
                                ? '<span class="text-green-600">Active</span>'
                                : '<span class="text-red-600">Inactive</span>'}
                        </td>
                    </tr>
                `;
            });
        });
}

// SEARCH (AUTO)
searchInput.addEventListener("input", () => {
    currentPage = 1;
    clearTimeout(window.searchTimer);
    window.searchTimer = setTimeout(loadMembers, 300);
});

// PAGINATION
document.getElementById("prevBtn").onclick = () => {
    if (currentPage > 1) {
        currentPage--;
        loadMembers();
    }
};

document.getElementById("nextBtn").onclick = () => {
    if (currentPage < totalPages) {
        currentPage++;
        loadMembers();
    }
};

// INIT
loadMembers();
