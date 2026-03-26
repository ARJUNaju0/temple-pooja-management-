// Initialize Lenis Smooth Scroll
const lenis = new Lenis({
  duration: 1.2,
  easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
  direction: 'vertical',
  smooth: true,
  mouseMultiplier: 1,
  smoothTouch: false,
  touchMultiplier: 2,
  infinite: false,
});

function raf(time) {
  lenis.raf(time);
  requestAnimationFrame(raf);
}

requestAnimationFrame(raf);

// Stop Lenis on anchor clicks
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener('click', function (e) {
    e.preventDefault();
    const target = document.querySelector(this.getAttribute('href'));
    if (target) {
      lenis.scrollTo(target, { offset: -80 });
    }
  });
});

// Hero Image Carousel - FIXED VERSION (No Blank Page)
function initHeroCarousel() {
  let heroImageContainer = document.querySelector('.hero-image img');
  if (!heroImageContainer) {
    console.log('Hero image container not found');
    return;
  }

  // Array of image paths - Update these with your actual image paths
  const images = [
    heroImageContainer.src, // Current image
    '/static/images/w4.jpg',
    '/static/images/w2.jpg',
    '/static/images/w3.jpg',
    '/static/images/w5.jpg',
    '/static/images/w6.jpg',
  ];

  // Only run carousel if there are multiple images
  if (images.length <= 1) {
    console.log('Hero carousel needs at least 2 images. Add more images to enable carousel.');
    return;
  }

  let currentIndex = 0;
  const intervalTime = 5000; // Change image every 5 seconds
  let isTransitioning = false;

  // Preload all images to prevent blank screen
  const preloadedImages = [];
  images.forEach((src, index) => {
    const img = new Image();
    img.src = src;
    preloadedImages[index] = img;
    console.log('Preloaded image:', src);
  });

  function changeImage() {
    // Prevent multiple transitions at once
    if (isTransitioning) return;
    
    // Double check container still exists
    if (!heroImageContainer || !heroImageContainer.parentNode) {
      console.error('Hero image container lost');
      return;
    }

    isTransitioning = true;
    const nextIndex = (currentIndex + 1) % images.length;
    
    // Create a new image element for crossfade effect
    const newImg = document.createElement('img');
    newImg.src = images[nextIndex];
    newImg.className = heroImageContainer.className;
    newImg.alt = heroImageContainer.alt;
    newImg.style.opacity = '0';
    newImg.style.position = 'absolute';
    newImg.style.inset = '0';
    newImg.style.width = '100%';
    newImg.style.height = '100%';
    newImg.style.objectFit = 'cover';
    
    // Get parent node
    const parent = heroImageContainer.parentNode;
    
    // Insert new image behind current one
    parent.insertBefore(newImg, heroImageContainer);
    
    // Crossfade: fade out old, fade in new
    gsap.to(heroImageContainer, {
      opacity: 0,
      duration: 1,
      ease: 'power2.inOut'
    });
    
    gsap.to(newImg, {
      opacity: 1,
      duration: 1,
      ease: 'power2.inOut',
      onComplete: () => {
        // Remove old image after transition
        const oldImg = heroImageContainer;
        heroImageContainer = newImg;
        
        // Safely remove old image
        if (oldImg && oldImg.parentNode) {
          oldImg.parentNode.removeChild(oldImg);
        }
        
        currentIndex = nextIndex;
        isTransitioning = false;
      }
    });
  }

  // Start the carousel after images are preloaded
  setTimeout(() => {
    setInterval(changeImage, intervalTime);
    console.log('Hero carousel started with', images.length, 'images');
  }, 1000);
}

// Initialize animations when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
  // Check if GSAP is loaded
  if (typeof gsap === 'undefined') {
    console.error('GSAP is not loaded!');
    return;
  }
  
  console.log('Initializing all animations...');
  initHeroTextSplitAnimation();
  initHeroCarousel();
  initScrollAnimations();
  initStackGallery();
  initTempleHistory();
});

// Hero Text Split Animation using GSAP
function initHeroTextSplitAnimation() {
  const heroTitle = document.querySelector('.hero-title');
  if (!heroTitle) {
    console.log('Hero title not found');
    return;
  }

  console.log('Initializing hero text animation...');

  // Split hero title into words with data attributes
  heroTitle.innerHTML = `
    <div class="title-line-1">
      <span class="word" data-direction="left">Welcome</span>
      <span class="word" data-direction="right">to</span>
    </div>
    <div class="title-line-2 text-gradient">
      <span class="word" data-direction="top">Kandakalankavu</span>
      <span class="word" data-direction="bottom">Temple</span>
    </div>
  `;

  // Animate words from different directions
  const words = heroTitle.querySelectorAll('.word');
  console.log(`Found ${words.length} words to animate`);
  
  words.forEach((word, index) => {
    const direction = word.getAttribute('data-direction');
    let xStart = 0, yStart = 0, rotation = 0;
    
    // Set starting position based on direction
    switch(direction) {
      case 'left':
        xStart = -200;
        rotation = -20;
        break;
      case 'right':
        xStart = 200;
        rotation = 20;
        break;
      case 'top':
        yStart = -150;
        rotation = -10;
        break;
      case 'bottom':
        yStart = 150;
        rotation = 10;
        break;
    }
    
    // GSAP animation for each word
    gsap.from(word, {
      x: xStart,
      y: yStart,
      rotation: rotation,
      opacity: 0,
      scale: 0.5,
      filter: 'blur(10px)',
      duration: 1.2,
      delay: index * 0.15,
      ease: 'back.out(1.7)',
      onComplete: function() {
        gsap.set(word, { clearProps: 'filter' });
      }
    });
  });

  // Animate subtitle with text split
  const subtitle = document.querySelector('.hero-subtitle');
  if (subtitle) {
    const subtitleText = subtitle.textContent.trim();
    const words = subtitleText.split(' ');
    
    // Wrap each word in a span with alternating directions
    subtitle.innerHTML = words.map((word, i) => {
      const direction = i % 2 === 0 ? 'left' : 'right';
      return `<span class="subtitle-word" data-direction="${direction}">${word}</span>`;
    }).join(' ');
    
    const subtitleWords = subtitle.querySelectorAll('.subtitle-word');
    
    subtitleWords.forEach((word, index) => {
      const direction = word.getAttribute('data-direction');
      const xStart = direction === 'left' ? -100 : 100;
      
      gsap.from(word, {
        x: xStart,
        opacity: 0,
        filter: 'blur(5px)',
        duration: 0.8,
        delay: 0.6 + (index * 0.08),
        ease: 'power3.out',
        onComplete: function() {
          gsap.set(word, { clearProps: 'filter' });
        }
      });
    });
  }

  // Animate buttons
  const heroContent = document.querySelector('.hero-content');
  if (heroContent) {
    const buttons = heroContent.querySelectorAll('a');
    buttons.forEach((btn, index) => {
      gsap.from(btn, {
        y: 100,
        opacity: 0,
        scale: 0.8,
        duration: 0.8,
        delay: 1.2 + (index * 0.1),
        ease: 'back.out(1.7)'
      });
    });
  }

  // Animate floating icon
  const floatingIcon = document.querySelector('.float');
  if (floatingIcon) {
    gsap.from(floatingIcon, {
      y: 100,
      opacity: 0,
      duration: 1,
      delay: 1.5,
      ease: 'power3.out'
    });
  }
}

// Scroll-triggered animations for other sections
function initScrollAnimations() {
  const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -100px 0px'
  };

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('animate-in');
        observer.unobserve(entry.target);
      }
    });
  }, observerOptions);

  // Observe all elements with animation classes
  document.querySelectorAll('.fade-up, .fade-left, .fade-right, .scale-in').forEach(el => {
    observer.observe(el);
  });
}

// Parallax effect for hero section
window.addEventListener('scroll', () => {
  const scrolled = window.pageYOffset;
  const heroImage = document.querySelector('.hero-image');
  
  if (heroImage) {
    heroImage.style.transform = `translateY(${scrolled * 0.5}px)`;
  }
});

// Stack Gallery Animation - FIXED VERSION
function initStackGallery() {
  if (typeof gsap === 'undefined') {
    console.log('GSAP not loaded, skipping stack gallery');
    return;
  }
  
  if (typeof ScrollTrigger === 'undefined') {
    console.log('ScrollTrigger not loaded, skipping stack gallery');
    return;
  }
  
  gsap.registerPlugin(ScrollTrigger);
  
  const stackCards = gsap.utils.toArray('.stack-card');
  if (stackCards.length === 0) {
    console.log('No stack cards found');
    return;
  }

  console.log(`Found ${stackCards.length} stack cards`);

  // Animate gallery title letters
  const galleryLetters = gsap.utils.toArray('.gallery-letter');
  if (galleryLetters.length > 0) {
    galleryLetters.forEach((letter, i) => {
      const directions = [
        { x: -100, rotation: -20 },
        { x: 100, rotation: 20 },
        { y: -100, rotation: 10 },
        { y: 100, rotation: -10 }
      ];
      const dir = directions[i % 4];
      
      gsap.from(letter, {
        opacity: 0,
        x: dir.x || 0,
        y: dir.y || 0,
        rotation: dir.rotation,
        scale: 0.5,
        duration: 0.8,
        delay: i * 0.05,
        ease: 'back.out(1.7)',
        scrollTrigger: {
          trigger: '#stack-gallery',
          start: 'top 80%',
          once: true
        }
      });
    });
  }

  // Stack cards animation with improved settings
  stackCards.forEach((card, index) => {
    const cardIndex = stackCards.length - index - 1;
    
    // Initial stacking - set immediately
    gsap.set(card, {
      y: cardIndex * 20,
      scale: 1 - (cardIndex * 0.05),
      transformOrigin: 'center center',
      zIndex: stackCards.length - cardIndex
    });

    // Create the fan-out animation
    const fanOutTimeline = gsap.timeline({
      scrollTrigger: {
        trigger: '#stack-gallery',
        start: 'top 60%',
        end: 'center 40%',
        scrub: 1.5,
        // markers: true, // Uncomment for debugging
      }
    });

    fanOutTimeline.to(card, {
      y: 0,
      scale: 1,
      rotation: (index - stackCards.length / 2) * 4,
      x: (index - stackCards.length / 2) * 80,
      ease: 'power2.out'
    });

    // Individual hover effect with better performance
    let hoverTween;
    
    card.addEventListener('mouseenter', () => {
      // Kill any existing hover animation
      if (hoverTween) hoverTween.kill();
      
      hoverTween = gsap.to(card, {
        scale: 1.08,
        zIndex: 1000,
        duration: 0.4,
        ease: 'power2.out',
        boxShadow: '0 20px 60px rgba(0,0,0,0.3)'
      });
    });

    card.addEventListener('mouseleave', () => {
      if (hoverTween) hoverTween.kill();
      
      hoverTween = gsap.to(card, {
        scale: 1,
        zIndex: stackCards.length - cardIndex,
        duration: 0.4,
        ease: 'power2.out',
        boxShadow: '0 10px 40px rgba(0,0,0,0.2)'
      });
    });
  });

  // Refresh ScrollTrigger after everything is set up
  ScrollTrigger.refresh();
}

// Temple History Animation
function initTempleHistory() {
  if (typeof gsap === 'undefined') {
    console.log('GSAP not loaded, skipping temple history');
    return;
  }
  
  if (typeof ScrollTrigger === 'undefined') {
    console.log('ScrollTrigger not loaded, skipping temple history');
    return;
  }
  
  gsap.registerPlugin(ScrollTrigger);

  // Animate history title letters with different directions
  const historyLetters = gsap.utils.toArray('.history-letter');
  if (historyLetters.length > 0) {
    historyLetters.forEach((letter, i) => {
      const angle = (i * 360 / historyLetters.length);
      const radius = 200;
      const x = Math.cos(angle * Math.PI / 180) * radius;
      const y = Math.sin(angle * Math.PI / 180) * radius;
      
      gsap.from(letter, {
        opacity: 0,
        x: x,
        y: y,
        scale: 0,
        rotation: angle,
        duration: 1.2,
        delay: i * 0.08,
        ease: 'elastic.out(1, 0.5)',
        scrollTrigger: {
          trigger: '.history-title',
          start: 'top 80%',
          once: true
        }
      });
    });
  }

  // Animate the line under title
  const historyLine = document.querySelector('.history-line');
  if (historyLine) {
    gsap.to(historyLine, {
      scaleX: 1,
      opacity: 1,
      duration: 1,
      ease: 'power3.out',
      scrollTrigger: {
        trigger: '.history-title',
        start: 'top 70%',
        once: true
      }
    });
  }

  // Animate history cards
  const historyCards = gsap.utils.toArray('.history-card');
  historyCards.forEach((card, index) => {
    gsap.to(card, {
      opacity: 1,
      y: 0,
      duration: 1,
      delay: index * 0.2,
      ease: 'power3.out',
      scrollTrigger: {
        trigger: card,
        start: 'top 85%',
        once: true
      }
    });

    // Parallax effect on scroll
    gsap.to(card, {
      y: -50,
      scrollTrigger: {
        trigger: card,
        start: 'top bottom',
        end: 'bottom top',
        scrub: 1,
      }
    });
  });

  // Animate timeline container
  const timelineContainer = document.querySelector('.timeline-container');
  if (timelineContainer) {
    gsap.to(timelineContainer, {
      opacity: 1,
      y: 0,
      duration: 1,
      scrollTrigger: {
        trigger: timelineContainer,
        start: 'top 80%',
        once: true
      }
    });
  }

  // Animate timeline items
  const timelineItems = gsap.utils.toArray('.timeline-item');
  timelineItems.forEach((item, index) => {
    gsap.to(item, {
      opacity: 1,
      x: 0,
      duration: 0.8,
      delay: index * 0.3,
      ease: 'power3.out',
      scrollTrigger: {
        trigger: item,
        start: 'top 90%',
        once: true
      }
    });
  });

  // Refresh ScrollTrigger
  ScrollTrigger.refresh();
}