// loading screen 
    const loadingScreen = document.getElementById('loading-screen');
    
    // Check if we've already loaded in this session
    const hasLoadedBefore = sessionStorage.getItem('hasLoaded');
    
    // If navigating within the page (not a reload), hide immediately
    if (hasLoadedBefore && performance.navigation.type !== 1) {
      loadingScreen.style.display = 'none';
    }

    // Hide loading screen after page loads
    window.addEventListener('load', function() {
      // Wait minimum time to show loader
      setTimeout(() => {
        loadingScreen.classList.add('hidden');
        
        // Mark that we've loaded once in this session
        sessionStorage.setItem('hasLoaded', 'true');
        
        // Remove from DOM after transition
        setTimeout(() => {
          loadingScreen.style.display = 'none';
        }, 500);
      }, 500);
    });

    // When navigating with links, mark navigation in progress
    document.addEventListener('click', function(e) {
      if (e.target.tagName === 'A' && e.target.href.includes('#')) {
        sessionStorage.setItem('isNavigating', 'true');
      }
    });