// D:\Django Internship\tprmsystem\main\static\js\lscript.js

const navbar = document.getElementById("navbar");
const brandName = document.getElementById("brandName");
const links = document.querySelectorAll(".nav-link");
const mobileMenu = document.getElementById("mobile-menu");
const menuButton = document.getElementById("mobile-menu-button");

let lastScroll = 0;
const currentPath = window.location.pathname.replace(/\/$/, "");
const isLoginPage = currentPath === "/login";
const isMemberProfilePage = currentPath === "/member/profile";
const isAdminDashboardPage = currentPath === "/temple_admin/dashboard";
const isAddmember = currentPath === "/temple_admin/add_member";
const isPoojas = currentPath === "/poojas"
const isAddPooja = currentPath === "/add";
const isEditPooja = currentPath.startsWith("/edit/");
const isManagePooja = currentPath === "/manage"
const isCalendar = currentPath === "/calendar";
const isServices = currentPath === "/services";
const isBookPooja = /^\/pooja\/\d+\/book\/?$/.test(currentPath);
const isMbHistory = currentPath === "/history";
const isAdHistory = currentPath === "/admin/all-bookings";
const isAMbHistory = currentPath.startsWith("/admin/bookings-by-member/");
const isGallery = currentPath === "/gallery";
const isImageUpload = currentPath === "/upload";
const isFamilyTreePage = currentPath === "/family";
const isBookingReport = currentPath === "/admin/reports/bookings";
const isPaymentReport = currentPath === "/admin/payment-report";
const isMainAllBookings = currentPath.startsWith("/admin/members")
const isBookingSuccess = currentPath.startsWith("/book/success")


const isSimpleNavbarPage =
    isLoginPage ||
    isMemberProfilePage ||
    isAdminDashboardPage ||
    isAddmember ||
    isPoojas ||
    isAddPooja ||
    isEditPooja ||
    isManagePooja ||
    isCalendar ||
    isServices ||
    isBookPooja ||
    isAMbHistory ||
    isAdHistory ||
    isGallery ||
    isImageUpload ||
    isMbHistory ||
    isFamilyTreePage ||
    isBookingReport ||
    isPaymentReport ||
    isMainAllBookings ||
    isBookingSuccess;

function applyLoginStyle() {
    navbar.classList.add("bg-white", "shadow-lg", "text-black");
    navbar.classList.remove("bg-transparent");

    brandName?.classList.add("text-black");
    brandName?.classList.remove("text-white");

    links.forEach(link => {
        link.classList.add("text-black");
        link.classList.remove("text-white");
    });
}

// Active link highlight
links.forEach(link => {
    const href = link.getAttribute("href");
    if (href) {
        const cleanHref = href.replace(/\/$/, "");
        if (cleanHref === currentPath) {
            link.classList.add(
                "decoration-2",
                "underline-offset-4",
                "underline",
                "shadow-md"
            );
        }
    }
});

// Scroll behavior
function updateNavbar() {
    const scrollY = window.scrollY;
    const scrollingDown = scrollY > lastScroll;

    if (isSimpleNavbarPage) {
        applyLoginStyle();
    } else {
        if (scrollY > 10) {
            navbar.classList.add("bg-white/90", "shadow-lg", "text-black");
            navbar.classList.remove("bg-transparent");
            brandName?.classList.add("text-black");
            brandName?.classList.remove("text-white");
        } else {
            navbar.classList.add("bg-transparent", "text-white");
            navbar.classList.remove("bg-white/90", "shadow-lg", "text-black");
            brandName?.classList.add("text-white");
            brandName?.classList.remove("text-black");
        }
    }

    if (scrollingDown && scrollY > 100 && !isLoginPage) {
        navbar.style.transform = "translateY(-100%)";
    } else {
        navbar.style.transform = "translateY(0)";
    }

    lastScroll = scrollY;
}

// Mobile menu toggle
menuButton?.addEventListener("click", () =>
    mobileMenu.classList.toggle("hidden")
);

// AUTHENTICATION & NAVBAR VISIBILITY

let authCache = null;
let cacheTime = 0;
const CACHE_DURATION = 5000;

// Check authentication status
async function checkAuthStatus() {
    try {
        const response = await fetch('/api/user/', {
            method: 'GET',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (response.ok) {
            return await response.json();
        }
        return null;
    } catch {
        return null;
    }
}

async function getCachedAuthStatus() {
    const now = Date.now();
    if (authCache && (now - cacheTime) < CACHE_DURATION) {
        return authCache;
    }
    authCache = await checkAuthStatus();
    cacheTime = now;
    return authCache;
}

async function updateNavbarAuth() {
    try {
        const userData = await checkAuthStatus();
        const isAuthenticated = !!userData;

        let userRole = null;
        let isStaff = false;

        if (userData) {
            userRole = userData.role || userData.user_type;
            isStaff = userData.is_staff || userData.staff || false;
        }

        const loginButton = document.getElementById('loginButton');
        const logoutButton = document.getElementById('logoutButton');
        const dashboardLink = document.getElementById('dashboardLink');
        const profileLink = document.getElementById('profileLink');
        const mobileLoginButton = document.getElementById('mobileLoginButton');
        const mobileLogoutButton = document.getElementById('mobileLogoutButton');
        const mobileDashboardLink = document.getElementById('mobileDashboardLink');
        const mobileProfileLink = document.getElementById('mobileProfileLink');

        if (isAuthenticated) {
            loginButton?.classList.add('hidden');
            logoutButton?.classList.remove('hidden');
            mobileLoginButton?.classList.add('hidden');
            mobileLogoutButton?.classList.remove('hidden');

            const isAdmin = isStaff || (userRole && userRole.toLowerCase().includes('admin'));

            if (!isAdmin && userRole === 'member') {
                dashboardLink?.classList.remove('hidden');
                profileLink?.classList.remove('hidden');
                mobileDashboardLink?.classList.remove('hidden');
                mobileProfileLink?.classList.remove('hidden');
            } else {
                dashboardLink?.classList.add('hidden');
                profileLink?.classList.add('hidden');
                mobileDashboardLink?.classList.add('hidden');
                mobileProfileLink?.classList.add('hidden');
            }
        } else {
            loginButton?.classList.remove('hidden');
            logoutButton?.classList.add('hidden');
            mobileLoginButton?.classList.remove('hidden');
            mobileLogoutButton?.classList.add('hidden');
            dashboardLink?.classList.add('hidden');
            profileLink?.classList.add('hidden');
            mobileDashboardLink?.classList.add('hidden');
            mobileProfileLink?.classList.add('hidden');
        }
    } catch {}
}

// Optimized update function
async function updateNavbarAuthFast() {
    try {
        const userData = authCache || await getCachedAuthStatus();
        const isAuthenticated = !!userData;

        let userRole = null;
        let isStaff = false;

        if (userData) {
            userRole = userData.role || userData.user_type;
            isStaff = userData.is_staff || userData.staff || false;
        }

        const loginButton = document.getElementById('loginButton');
        const logoutButton = document.getElementById('logoutButton');
        const adminDashboardLink = document.getElementById('adminDashboardLink');
        const dashboardLink = document.getElementById('dashboardLink');
        const profileLink = document.getElementById('profileLink');
        const mobileLoginButton = document.getElementById('mobileLoginButton');
        const mobileLogoutButton = document.getElementById('mobileLogoutButton');
        const mobileAdminDashboardLink = document.getElementById('mobileAdminDashboardLink');
        const mobileDashboardLink = document.getElementById('mobileDashboardLink');
        const mobileProfileLink = document.getElementById('mobileProfileLink');

        if (isAuthenticated) {
            loginButton?.classList.add('hidden');
            logoutButton?.classList.remove('hidden');
            mobileLoginButton?.classList.add('hidden');
            mobileLogoutButton?.classList.remove('hidden');

            const isAdmin = isStaff || (userRole && userRole.toLowerCase().includes('admin'));

            if (isAdmin) {
                adminDashboardLink?.classList.remove('hidden');
                mobileAdminDashboardLink?.classList.remove('hidden');

                dashboardLink?.classList.add('hidden');
                profileLink?.classList.add('hidden');
                mobileDashboardLink?.classList.add('hidden');
                mobileProfileLink?.classList.add('hidden');
            } else if (userRole === 'member') {
                dashboardLink?.classList.remove('hidden');
                profileLink?.classList.remove('hidden');
                mobileDashboardLink?.classList.remove('hidden');
                mobileProfileLink?.classList.remove('hidden');

                adminDashboardLink?.classList.add('hidden');
                mobileAdminDashboardLink?.classList.add('hidden');
            }
        } else {
            loginButton?.classList.remove('hidden');
            logoutButton?.classList.add('hidden');
            mobileLoginButton?.classList.remove('hidden');
            mobileLogoutButton?.classList.add('hidden');

            adminDashboardLink?.classList.add('hidden');
            dashboardLink?.classList.add('hidden');
            profileLink?.classList.add('hidden');
            mobileAdminDashboardLink?.classList.add('hidden');
            mobileDashboardLink?.classList.add('hidden');
            mobileProfileLink?.classList.add('hidden');
        }
    } catch {}
}

// Logout handler
async function handleLogout() {
    // Create a promise that resolves when user confirms or rejects
    const userConfirmed = await new Promise((resolve) => {
        // Create overlay
        const overlay = document.createElement('div');
        overlay.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        
        // Create confirmation dialog
        const dialog = document.createElement('div');
        dialog.className = 'bg-white rounded-lg p-6 max-w-md w-full mx-4 shadow-xl';
        
        // Add dialog content
        dialog.innerHTML = `
            <div class="text-center">
                <div class="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                    </svg>
                </div>
                <h3 class="text-lg font-medium text-gray-900 mb-2">Logout Confirmation</h3>
                <p class="text-gray-600 mb-6">Are you sure you want to logout?</p>
                <div class="flex justify-center space-x-4">
                    <button id="cancelLogout" class="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500">
                        Cancel
                    </button>
                    <button id="confirmLogout" class="px-4 py-2 border border-transparent rounded-md shadow-sm text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500">
                        Logout
                    </button>
                </div>
            </div>
        `;
        
        // Append elements to body
        overlay.appendChild(dialog);
        document.body.appendChild(overlay);
        document.body.style.overflow = 'hidden'; // Prevent scrolling
        
        // Handle button clicks
        dialog.querySelector('#confirmLogout').addEventListener('click', () => {
            cleanup();
            resolve(true);
        });
        
        dialog.querySelector('#cancelLogout').addEventListener('click', () => {
            cleanup();
            resolve(false);
        });
        
        // Cleanup function
        function cleanup() {
            overlay.remove();
            document.body.style.overflow = '';
        }
    });
    
    if (!userConfirmed) return;
    
    try {
        const response = await fetch('/api/logout/', {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (response.ok) {
            // Show success toast before redirect
            window.dispatchEvent(new CustomEvent('show-toast', {
                detail: {
                    message: 'You have been logged out successfully.',
                    type: 'success'
                }
            }));
        }
        
        sessionStorage.removeItem('user');
        
        // Small delay to show the toast before redirect
        setTimeout(() => {
            window.location.href = '/';
        }, 1000);
        
    } catch (error) {
        console.error('Logout error:', error);
        window.dispatchEvent(new CustomEvent('show-toast', {
            detail: {
                message: 'Error during logout. Please try again.',
                type: 'error'
            }
        }));
    }
}

// Make the function globally available
window.handleLogout = handleLogout;

// INITIALIZATION


(async function() {
    authCache = await checkAuthStatus();
    cacheTime = Date.now();
})();

updateNavbarAuthFast();
window.addEventListener("scroll", updateNavbar);

document.addEventListener('DOMContentLoaded', () => {
    updateNavbar();
    updateNavbarAuthFast();
    setTimeout(updateNavbar, 100);
});

window.addEventListener('storage', () => {
    authCache = null;
    updateNavbarAuth();
});

document.addEventListener("DOMContentLoaded", function () {
    const images = document.querySelectorAll(".lazy-img");

    const observer = new IntersectionObserver(
        (entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.classList.remove("opacity-0");
                    img.classList.add("opacity-100");
                    observer.unobserve(img);
                }
            });
        },
        {
            rootMargin: "100px",
            threshold: 0.1
        }
    );

    images.forEach(img => observer.observe(img));
});


function getCSRFToken() {
    const cookieValue = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrftoken='))
        ?.split('=')[1];
    return cookieValue || '';
}

function getAuthToken() {
    return localStorage.getItem('authToken') || '';
}

document.addEventListener('click', function(event) {
    // Check if the clicked element is a delete button or a child of one
    const deleteBtn = event.target.closest('.delete-btn');
    if (!deleteBtn) return;
        
    const imageId = deleteBtn.getAttribute('data-image-id');
    if (!imageId) return;
    
    if (!confirm("Are you sure you want to delete this image?")) {
        return;
    }

    fetch(`/gallery/delete/${imageId}/`, {
        method: "POST",
        headers: {
            "X-CSRFToken": getCSRFToken(),
            "Content-Type": "application/json",
        },
        credentials: 'include',
        body: JSON.stringify({})
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => {
                throw new Error(err.error || 'Failed to delete image');
            });
        }
        return response.json();
    })
    .then(data => {
        if (data && data.success) {
            alert("Image deleted successfully");
            location.reload();
        } else {
            throw new Error(data?.error || "Unknown error occurred");
        }
    })
    .catch(err => {
        console.error("Delete error:", err);
        alert("Delete failed: " + (err.message || "Unknown error occurred"));
    });
});