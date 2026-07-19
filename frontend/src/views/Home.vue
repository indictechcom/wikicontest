<template>
  <div>

    <!-- HERO SECTION - Professional Clean Design -->
    <!-- Main landing page hero with title, description, and call-to-action buttons -->
    <section class="hero">
      <div class="container">
        <div class="hero-content">
          <h1 class="hero-title">WikiContest</h1>
          <p class="hero-subtitle">Collaborate. Compete. Create Knowledge.</p>
          <p class="hero-description">
            A professional platform for managing Wikipedia article contests and
            fostering collaborative knowledge creation.
          </p>

          <!-- Primary action buttons for navigation -->
          <div class="hero-buttons">
            <!-- Browse contests button - always visible -->
            <router-link class="btn btn-primary btn-lg" to="/contests">Browse Contests</router-link>
            <!-- Get started button - redirects to OAuth if not logged in, dashboard if logged in -->
            <a
              @click.prevent="handleGetStarted"
              class="btn btn-outline-primary btn-lg"
              title="Get started with Wikimedia OAuth authentication"
            >
              Get Started
            </a>
          </div>
        </div>
      </div>
    </section>

    <!-- FEATURES -->
    <!-- Feature cards explaining platform benefits for different user types -->
    <section class="features container py-5">
      <div class="row g-4">

        <!-- Participant features card -->
        <div class="col-12 col-md-4">
          <div class="feature-card">
            <i class="fas fa-users icon"></i>
            <h3>Participants</h3>
            <p>Submit articles, collaborate, and compete in global contests.</p>
          </div>
        </div>

        <!-- Organizer features card -->
        <div class="col-12 col-md-4">
          <div class="feature-card">
            <i class="fas fa-plus-circle icon"></i>
            <h3>Organizers</h3>
            <p>Create contests, manage tasks, and engage communities.</p>
          </div>
        </div>

        <!-- Judge features card -->
        <div class="col-12 col-md-4">
          <div class="feature-card">
            <i class="fas fa-gavel icon"></i>
            <h3>Judges</h3>
            <p>Review submissions and ensure fair evaluation.</p>
          </div>
        </div>

      </div>
    </section>

  </div>
</template>


<script>
import { useStore } from '../store'
import { useRouter } from 'vue-router'

export default {
  name: 'Home',
  setup() {
    const store = useStore()
    const router = useRouter()

    return {
      store,
      router
    }
  },
  methods: {
    // Handle "Get Started" button click
    // If user is logged in, navigate to organizer dashboard
    // Otherwise, redirect to OAuth login
    async handleGetStarted() {
      // Check if user is authenticated
      const isAuthenticated = this.store.isAuthenticated

      if (isAuthenticated) {
        // User is logged in - navigate to organizer dashboard
        this.router.push('/organizer/dashboard')
      } else {
        // User is not logged in - redirect to OAuth login
        window.location.href = this.getOAuthUrl()
      }
    },
    // Get MediaWiki OAuth URL - directly opens MediaWiki authentication
    // This bypasses the login/register page and goes straight to OAuth
    getOAuthUrl() {
      // In development, use full URL to Flask backend
      if (import.meta.env.DEV) {
        return 'http://localhost:5000/api/user/oauth/login'
      }
      // In production, use relative URL
      return '/api/user/oauth/login'
    }
  }
}
</script>

<style scoped>
/* Hero section - professional solid background */
.hero {
  background-color: var(--wiki-primary);
  color: #ffffff;
  padding: 5rem 0;
  margin-top: 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

/* Dark mode hero background */
[data-theme="dark"] .hero {
  background-color: #1a2332;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

/* Hero content container */
.hero-content {
  text-align: center;
  max-width: 800px;
  margin: 0 auto;
  padding: 0 1rem;
}

/* Hero title - professional typography */
.hero-title {
  font-size: 3rem;
  font-weight: 700;
  margin-bottom: 1rem;
  color: #ffffff;
  letter-spacing: -0.02em;
}

/* Hero subtitle */
.hero-subtitle {
  font-size: 1.5rem;
  font-weight: 500;
  margin-bottom: 0.75rem;
  color: rgba(255, 255, 255, 0.95);
}

/* Hero description */
.hero-description {
  font-size: 1.1rem;
  line-height: 1.6;
  margin-bottom: 2.5rem;
  color: rgba(255, 255, 255, 0.85);
  max-width: 600px;
  margin-left: auto;
  margin-right: auto;
}

/* Hero buttons container */
.hero-buttons {
  display: flex;
  gap: 1rem;
  justify-content: center;
  flex-wrap: wrap;
}

/* Professional button styling */
.hero-buttons .btn {
  padding: 0.75rem 2rem;
  font-weight: 600;
  border-radius: 4px;
  transition: all 0.2s ease;
  text-decoration: none;
}

/* Primary button - white on colored background */
.hero-buttons .btn-primary {
  background-color: #ffffff;
  color: var(--wiki-primary);
  border: 1px solid #ffffff;
}

/* Primary button hover with lift effect */
.hero-buttons .btn-primary:hover {
  background-color: rgba(255, 255, 255, 0.95);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

/* Outline button - transparent with border */
.hero-buttons .btn-outline-primary {
  background-color: transparent;
  color: #ffffff;
  border: 2px solid rgba(255, 255, 255, 0.8);
}

/* Outline button hover with subtle background */
.hero-buttons .btn-outline-primary:hover {
  background-color: rgba(255, 255, 255, 0.1);
  border-color: #ffffff;
  color: #ffffff;
}

.features {
  background-color: var(--wiki-light-bg);
  padding: 4rem 0;
}

/* Dark mode features section */
[data-theme="dark"] .features {
  background-color: var(--wiki-bg);
}

/* Professional feature cards */
.feature-card {
  background-color: var(--wiki-card-bg);
  border: 1px solid var(--wiki-border);
  border-radius: 6px;
  padding: 2rem;
  text-align: center;
  height: 100%;
  transition: all 0.2s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

/* Dark mode feature card shadow */
[data-theme="dark"] .feature-card {
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
}

/* Subtle hover effect with lift and border highlight */
.feature-card:hover {
  border-color: var(--wiki-primary);
  box-shadow: 0 4px 12px rgba(0, 102, 153, 0.12);
  transform: translateY(-2px);
}

/* Dark mode hover effect */
[data-theme="dark"] .feature-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
}

/* Professional icon styling */
.icon {
  font-size: 2.5rem;
  margin-bottom: 1rem;
  color: var(--wiki-primary);
  transition: color 0.2s ease;
}

/* Icon color change on card hover */
.feature-card:hover .icon {
  color: var(--wiki-primary-hover);
}

/* Card title */
.feature-card h3 {
  font-size: 1.25rem;
  font-weight: 600;
  margin-bottom: 0.75rem;
  color: var(--wiki-dark);
  letter-spacing: -0.01em;
}

/* Card description */
.feature-card p {
  font-size: 0.95rem;
  line-height: 1.6;
  color: var(--wiki-text-muted);
  margin: 0;
}

/* Tablet and smaller devices */
@media (max-width: 768px) {
  .hero {
    padding: 3.5rem 0;
  }

  .hero-title {
    font-size: 2.25rem;
  }

  .hero-subtitle {
    font-size: 1.25rem;
  }

  .hero-description {
    font-size: 1rem;
    margin-bottom: 2rem;
  }

  /* Stack buttons vertically on mobile */
  .hero-buttons {
    flex-direction: column;
    align-items: stretch;
  }

  .hero-buttons .btn {
    width: 100%;
  }

  .features {
    padding: 3rem 0;
  }

  .feature-card {
    padding: 1.5rem;
  }
}

/* Mobile devices */
@media (max-width: 576px) {
  .hero-title {
    font-size: 1.875rem;
  }

  .hero-subtitle {
    font-size: 1.125rem;
  }

  .feature-card {
    padding: 1.25rem;
  }

  .icon {
    font-size: 2rem;
  }
}

</style>
