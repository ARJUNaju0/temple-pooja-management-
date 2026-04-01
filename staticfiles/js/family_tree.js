/*************************************************
 * FAMILY TREE – TEMPLE STYLE (FINAL)
 *************************************************/

document.addEventListener('DOMContentLoaded', () => {
    loadTree();
    if (typeof IS_ADMIN !== 'undefined' && IS_ADMIN) {
        loadTableAndDropdowns();
    }
});

/* ================================
   API HELPERS
================================ */
async function fetchAPI(url, method = 'GET', body = null) {
    const headers = {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken')
    };
    const config = { method, headers };
    if (body) config.body = JSON.stringify(body);
    return await fetch(url, config);
}

function getCookie(name) {
    let cookieValue = null;
    document.cookie.split(';').forEach(cookie => {
        cookie = cookie.trim();
        if (cookie.startsWith(name + '=')) {
            cookieValue = decodeURIComponent(cookie.slice(name.length + 1));
        }
    });
    return cookieValue;
}

/* ================================
   TREE LOADER
================================ */
async function loadTree() {
    const res = await fetchAPI('/api/members/tree_structure/');
    const data = await res.json();
    renderChart(data);
}

/* ================================
   D3 TREE RENDER (UPDATED)
================================ */
function renderChart(data) {
    const container = document.getElementById('tree-svg-container');
    container.innerHTML = '';

    // Get container dimensions
    const containerWidth = container.parentElement.offsetWidth;
    const containerHeight = 600; // Match the height from HTML
    
    const nodeWidth = 200;
    const nodeHeight = 140;

    // Create SVG that will expand with content
    const svg = d3.select(container)
        .append('svg')
        .attr('width', '100%')
        .attr('height', '100%')
        .style('min-width', '100%')
        .style('min-height', '100%');
        
    // Add a group that will contain all the tree elements with zoom behavior
    const g = svg.append('g');
    
    // Initialize zoom behavior
    const zoom = d3.zoom()
        .scaleExtent([0.5, 3])
        .on('zoom', (event) => {
            g.attr('transform', event.transform);
        });
    
    // Set initial zoom and center
    const initialScale = 1.2;
    
    // Apply zoom behavior to the SVG but disable wheel/scroll zoom
    svg.call(zoom)
      .on('wheel.zoom', null)  // Disable wheel/scroll zoom
      .on('dblclick.zoom', null)  // Optionally disable double-click zoom as well
      .call(zoom.scaleTo, 1.2);  // Set initial zoom level to 1.2x
    
    // Add zoom button event listeners
    document.querySelector('.zoom-in-btn')?.addEventListener('click', () => {
        svg.transition().duration(300).call(zoom.scaleBy, 1.2);
    });
    
    document.querySelector('.zoom-out-btn')?.addEventListener('click', () => {
        svg.transition().duration(300).call(zoom.scaleBy, 0.8);
    });

    // Calculate initial dimensions based on the data
    const treeLayout = d3.tree().nodeSize([nodeWidth, nodeHeight]);
    const root = d3.hierarchy(data);
    
    // Initial layout to get dimensions
    treeLayout(root);
    
    // Find the bounds of the tree
    let x0 = Infinity;
    let x1 = -Infinity;
    let y0 = Infinity;
    let y1 = -Infinity;
    
    root.each(d => {
        if (d.x > x1) x1 = d.x;
        if (d.x < x0) x0 = d.x;
        if (d.y > y1) y1 = d.y;
        if (d.y < y0) y0 = d.y;
    });
    
    // Add padding
    const padding = 80; // Increased padding for better spacing
    x0 -= padding;
    x1 += padding + nodeWidth;  // Account for node width
    y0 -= padding;
    y1 += padding + nodeHeight; // Account for node height
    
    // Calculate the required width and height
    const treeWidth = x1 - x0;
    const treeHeight = y1 - y0;
    
    // Set the container size to fit the tree
    container.style.width = `${Math.max(treeWidth, containerWidth)}px`;
    container.style.height = `${Math.max(treeHeight, containerHeight)}px`;
    
    // Calculate center position
    const centerX = (containerWidth - treeWidth) / 2 - x0;
    const centerY = (containerHeight - treeHeight) / 2 - y0 + 20; // Small top margin
    
    // Apply initial transform to center the tree
    svg.call(zoom.transform, d3.zoomIdentity.translate(centerX, centerY));

    // Initial Collapse (Optional)
    if (root.data.is_virtual_root && root.children) {
        root.children.forEach(collapse);
    }
    
    update(root);

    function collapse(d) {
        if (d.children) {
            d._children = d.children;
            d._children.forEach(collapse);
            d.children = null;
        }
    }

    function update(source) {
        const treeData = treeLayout(root);
        const nodes = treeData.descendants();
        const links = treeData.links();
        
        // Center the tree by adjusting the root node's position
        if (!source) {
            // Find the leftmost and rightmost nodes to calculate width
            let minX = Infinity, maxX = -Infinity;
            nodes.forEach(d => {
                if (d.x < minX) minX = d.x;
                if (d.x > maxX) maxX = d.x;
            });
            
            // Calculate the offset needed to center the tree
            const treeWidth = maxX - minX;
            const offsetX = (width - treeWidth) / 2 - minX;
            
            // Apply the offset to all nodes
            nodes.forEach(d => {
                d.x += offsetX;
            });
        }

        // 1. Create a Map to find nodes by ID easily
        const nodeById = new Map();
        nodes.forEach(n => nodeById.set(n.data.id, n));

        // 2. Adjust Spouse Positions
        // We move the spouse to the right of the main node
        nodes.forEach(d => {
            if (d.data.spouse_id) {
                const spouse = nodeById.get(d.data.spouse_id);
                // Only move if spouse exists and is currently in the view
                if (spouse && d.data.id < spouse.data.id) {
                    // Place spouse to the right
                    spouse.x = d.x + 100; // Shift amount
                    spouse.y = d.y;
                }
            }
        });

        // ==========================================================
        // DRAW NODES
        // ==========================================================
        const node = g.selectAll('g.node')
            .data(nodes, d => d.data.id);

        const nodeEnter = node.enter()
            .append('g')
            .attr('class', 'node')
            .attr('transform', d => `translate(${source.x0 || source.x},${source.y0 || source.y})`)
            .on('click', (e, d) => {
                // Toggle children on click
                if (d.children) {
                    d._children = d.children;
                    d.children = null;
                } else {
                    d.children = d._children;
                    d._children = null;
                }
                update(d);
            });

        // Node Circle with gender-based colors
        nodeEnter.append('circle')
            .attr('r', 20)
            .attr('fill', '#fff')
            .attr('stroke', d => {
                // Debugging: Log the gender value
                console.log('Node:', d.data.name, 'Gender:', d.data.gender);
                return d.data.gender === 'M' ? '#3B82F6' : '#EC4899';
            })
            .attr('stroke-width', 3)  // Slightly thicker stroke for better visibility
            .style('filter', 'drop-shadow(0 0 2px rgba(0,0,0,0.2))');  // Add subtle shadow

        // Node Image (if exists)
        nodeEnter.append('image')
            .attr('href', d => d.data.photo || '/static/img/default-fam.jpg')
            .attr('x', -20).attr('y', -20)
            .attr('width', 40).attr('height', 40)
            .attr('clip-path', 'circle(20px at 20px 20px)');

       // Find the "Name Label" section in your renderChart function and replace it with this:

// Name Label with special handling for virtual root
const nameText = nodeEnter.append('text')
    .attr('y', 35)  // Position below the circle (20px radius + 15px spacing)
    .attr('text-anchor', 'middle')
    .style('font-size', d => d.data.is_virtual_root ? '10px' : '12px')
    .style('font-weight', 'bold');
    
nameText.each(function(d) {
    const name = d.data.is_virtual_root ? 'Thottamon Tarawad' : d.data.name;
    const words = name.split(' ');
    const text = d3.select(this);
    
    // Always split into 3 lines
    const partLength = Math.ceil(words.length / 3);
    const line1 = words.slice(0, partLength).join(' ');
    const line2 = words.slice(partLength, partLength * 2).join(' ');
    const line3 = words.slice(partLength * 2).join(' ');
    
    // Always create exactly 3 tspans for consistent spacing
    text.append('tspan')
        .attr('x', 0)
        .attr('dy', '0')
        .text(line1 || '');
    
    text.append('tspan')
        .attr('x', 0)
        .attr('dy', '1.2em')
        .text(line2 || '');
    
    text.append('tspan')
        .attr('x', 0)
        .attr('dy', '1.2em')
        .text(line3 || '');
});

        // Update positions
        const nodeUpdate = node.merge(nodeEnter).transition().duration(500)
            .attr('transform', d => `translate(${d.x},${d.y})`);

        node.exit().remove();

        // ==========================================================
        // DRAW SPOUSE CONNECTOR (Dashed Line)
        // ==========================================================
        // Filter relationships where both partners are visible
        const spouseLinks = [];
        nodes.forEach(d => {
            if (d.data.spouse_id) {
                const spouse = nodeById.get(d.data.spouse_id);
                if (spouse && d.data.id < spouse.data.id) {
                    spouseLinks.push({ source: d, target: spouse });
                }
            }
        });

        const sl = g.selectAll('path.spouse-link')
            .data(spouseLinks, d => d.source.data.id + '-' + d.target.data.id);

        sl.enter().insert('path', 'g')
            .attr('class', 'spouse-link')
            .attr('fill', 'none')
            .attr('stroke', '#666')
            .attr('stroke-dasharray', '4,4') // Dashed look
            .attr('d', d => `M${d.source.x},${d.source.y} L${d.target.x},${d.target.y}`)
            .merge(sl)
            .transition().duration(500)
            .attr('d', d => `M${d.source.x},${d.source.y} L${d.target.x},${d.target.y}`);

        sl.exit().remove();

        // ==========================================================
        // DRAW PARENT -> CHILD LINKS (The "T" Shape)
        // ==========================================================
        const linksData = links.filter(d => d.source.data.id !== 'root'); // skip virtual root

        const link = g.selectAll('path.link')
            .data(linksData, d => d.target.data.id);

        link.enter().insert('path', 'g')
            .attr('class', 'link')
            .attr('fill', 'none')
            .attr('stroke', '#ccc')
            .attr('stroke-width', 2)
            .attr('d', d => {
                const o = { x: source.x0 || source.x, y: source.y0 || source.y };
                return elbow({ source: o, target: o });
            })
            .merge(link)
            .transition().duration(500)
            .attr('d', d => {
                // LOGIC TO CENTER THE PARENT START POINT
                let parentX = d.source.x;
                let parentY = d.source.y;
                
                // If parent has a spouse, start from the MIDDLE of the couple
                if (d.source.data.spouse_id) {
                    const spouse = nodeById.get(d.source.data.spouse_id);
                    if (spouse) {
                        parentX = (d.source.x + spouse.x) / 2;
                    }
                }
                
                return elbow({
                    source: { x: parentX, y: parentY },
                    target: d.target
                });
            });

        link.exit().remove();

        // Stash positions for transitions
        nodes.forEach(d => {
            d.x0 = d.x;
            d.y0 = d.y;
        });
    }

    // Helper: Draw Orthogonal (Elbow) Lines
    // This creates the rigid family tree structure
    function elbow(d) {
        const midY = (d.source.y + d.target.y) / 2;
        return `M${d.source.x},${d.source.y}
                V${midY}
                H${d.target.x}
                V${d.target.y}`;
    }
}

/* ================================
   ADMIN CRUD
================================ */
let allMembers = [];

async function loadTableAndDropdowns() {
    const res = await fetchAPI('/api/members/');
    allMembers = await res.json();

    const tbody = document.getElementById('member-table-body');
    tbody.innerHTML = allMembers.map(m => `
        <tr>
            <td class="px-6 py-4">${m.name}</td>
            <td class="px-6 py-4">${m.gender}</td>
            <td class="px-6 py-4">${m.parent_name || '-'}</td>
            <td class="px-6 py-4 text-right">
                <button onclick="editMember(${m.id})" class="text-indigo-600 mr-2">Edit</button>
                <button onclick="deleteMember(${m.id})" class="text-red-600">Delete</button>
            </td>
        </tr>
    `).join('');

    ['parentSelect', 'spouseSelect'].forEach(id => {
        const select = document.getElementById(id);
        const first = select.options[0].outerHTML;
        select.innerHTML = first + allMembers.map(m =>
            `<option value="${m.id}">${m.name}</option>`
        ).join('');
    });
}

async function deleteMember(id) {
    // Show confirmation toast
    const confirmed = await new Promise((resolve) => {
        const toast = document.createElement('div');
        toast.className = 'fixed right-4 top-4 px-6 py-3 rounded-lg bg-yellow-600 text-white font-medium shadow-lg z-50 flex flex-col items-end';
        toast.innerHTML = `
            <p class="mb-3">Are you sure you want to delete this member?</p>
            <div class="flex gap-2">
                <button class="px-3 py-1 bg-red-600 rounded hover:bg-red-700" id="confirm-delete">Delete</button>
                <button class="px-3 py-1 bg-gray-500 rounded hover:bg-gray-600" id="cancel-delete">Cancel</button>
            </div>
        `;
        document.body.appendChild(toast);

        // Remove toast after 10 seconds if no action is taken
        const timeout = setTimeout(() => {
            document.body.removeChild(toast);
            resolve(false);
        }, 10000);

        // Handle button clicks
        document.getElementById('confirm-delete').onclick = () => {
            clearTimeout(timeout);
            document.body.removeChild(toast);
            resolve(true);
        };
        document.getElementById('cancel-delete').onclick = () => {
            clearTimeout(timeout);
            document.body.removeChild(toast);
            resolve(false);
        };
    });

    if (!confirmed) return;
    
    try {
        await fetchAPI(`/api/members/${id}/`, 'DELETE');
        window.showToast('Member deleted successfully', 'success');
        loadTableAndDropdowns();
        loadTree();
    } catch (error) {
        window.showToast('Failed to delete member', 'error');
        console.error('Error deleting member:', error);
    }
}

/* ================================
   ADMIN MODAL HANDLERS
================================ */
function openModal() {
    document.getElementById('memberForm').reset();
    document.getElementById('memberId').value = '';
    document.getElementById('modalTitle').innerText = 'Add Member';
    document.getElementById('memberModal').classList.remove('hidden');
}

function closeModal() {
    document.getElementById('memberModal').classList.add('hidden');
}

function editMember(id) {
    const member = allMembers.find(m => m.id === id);
    if (!member) return;

    document.getElementById('memberId').value = member.id;
    document.getElementById('name').value = member.name;
    document.getElementById('gender').value = member.gender;
    document.getElementById('parentSelect').value = member.parent || '';
    document.getElementById('spouseSelect').value = member.spouse_id || '';

    document.getElementById('modalTitle').innerText = 'Edit Member';
    document.getElementById('memberModal').classList.remove('hidden');
}

/* ================================
   FORM SUBMIT
================================ */
document.getElementById('memberForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const id = document.getElementById('memberId').value;

    const formData = new FormData();
    formData.append('name', document.getElementById('name').value);
    formData.append('gender', document.getElementById('gender').value);
    formData.append('parent', document.getElementById('parentSelect').value || '');
    formData.append('spouse', document.getElementById('spouseSelect').value || '');
    formData.append('date_of_birth', document.getElementById('dob')?.value || '');
    formData.append('notes', document.getElementById('notes')?.value || '');
    const photoFile = document.getElementById('photo').files[0];
    if (photoFile) formData.append('photo', photoFile);

    const url = id ? `/api/members/${id}/` : '/api/members/';
    const method = id ? 'PUT' : 'POST';

    const headers = {
        'X-CSRFToken': getCookie('csrftoken'),
    };

    const res = await fetch(url, { method, headers, body: formData });

    if (res.ok) {
        closeModal();
        window.showToast(`Member ${id ? 'updated' : 'added'} successfully`, 'success');
        loadTableAndDropdowns();
        loadTree();
    } else {
        const err = await res.json();
        window.showToast(`Error: ${JSON.stringify(err)}`, 'error');
        console.error('Form submission error:', err);
    }
});