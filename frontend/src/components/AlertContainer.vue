<template>
  <div
    id="alertContainer"
    class="position-fixed end-0 p-3"
     style="z-index: 9999; top: 80px;"
  >
    <!-- Transition group provides smooth enter/leave animations for alerts -->
    <transition-group name="alert" tag="div">
      <!-- Individual alert cards with dynamic type-based styling -->
      <div
        v-for="alert in alerts"
        :key="alert.id"
        :class="['alert-card', `alert-${alert.type}`]"
        role="alert"
      >
        <div class="alert-content">
          <!-- Alert message text -->
          <span class="alert-message">{{ alert.message }}</span>
          <!-- Close button for manual dismissal -->
          <button type="button" class="close-btn" @click="removeAlert(alert.id)">×</button>
        </div>
      </div>
    </transition-group>
  </div>
</template>

<script>
import { getAlertState, removeAlert } from '../utils/alerts'
export default {
  name: 'AlertContainer',
  setup() {
    // Get reactive alert state from centralized alert utility
    // Ensures all components share the same alert queue
    const alertState = getAlertState()
    return {
      alerts: alertState.alerts,
      removeAlert
    }
  }
}
</script>

<style scoped>


/* Container positioning and sizing */
#alertContainer {
  max-width: 420px;
  right: 1rem;
}

/* --- Animations (fade + slide + slight scale) --- */
.alert-enter-active,
.alert-leave-active {
  transition: all 0.35s cubic-bezier(0.25, 0.1, 0.25, 1);
}

.alert-enter-from,
.alert-leave-to {
  opacity: 0;
  transform: translateX(40px) scale(0.97);
}

.alert-card {
  width: 100%;
  padding: 1rem 1.3rem;
  margin-bottom: 1rem;

  border-radius: 5px;

  /* Glass effect */
  /* Glassmorphism provides modern, premium aesthetic */
  background: rgba(255, 255, 255, 0.35);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);

  border: 1px solid rgba(255, 255, 255, 0.4);

  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.15);

  color: #000;
  font-size: 0.95rem;
  font-weight: 500;
  overflow: hidden;

  display: flex;
  justify-content: space-between;
}

/* Hover Lift */
/* Subtle elevation provides interactive feedback */
.alert-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.25);
}

.alert-content {
  display: flex;
  justify-content: space-between;
  width: 100%;
  align-items: center;
}

.alert-message {
  line-height: 1.4;
}

/* Close Button */
/* Circular button with semi-transparent background */
.close-btn {
  background: rgba(255, 255, 255, 0.6);
  border: none;
  border-radius: 50%;
  width: 26px;
  height: 26px;

  font-size: 1rem;
  font-weight: bold;
  color: #444;

  cursor: pointer;
  transition: 0.25s ease;
}

/* Playful rotation on hover for better UX */
.close-btn:hover {
  transform: scale(1.18) rotate(10deg);
  background: rgba(255, 255, 255, 0.85);
}

.alert-card {
  position: relative;
}

/* Colored left border indicates alert type at a glance */
.alert-card::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0;
  width: 8px;
  height: 100%;
  border-radius: 5px 0 0 5px;
}

/* Success – green */
.alert-success::before {
  background: #2ecc71;
}

/* Danger – red */
.alert-danger::before {
  background: #e74c3c;
}

/* Info – blue */
.alert-info::before {
  background: #3498db;
}

/* Warning – orange */
.alert-warning::before {
  background: #f39c12;
}

/* Dark mode adjusts glassmorphism for better contrast */
[data-theme="dark"] .alert-card {
  background: rgba(40, 40, 40, 0.55);
  border-color: rgba(255, 255, 255, 0.12);
  color: #eee;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.45);
}

[data-theme="dark"] .close-btn {
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
}

[data-theme="dark"] .close-btn:hover {
  background: rgba(255, 255, 255, 0.35);
}

/* Mobile optimizations for smaller screens */
@media (max-width: 768px) {
  #alertContainer {
    max-width: 92%;
  }
  .alert-card {
    padding: 0.85rem 1rem;
  }
}
</style>
