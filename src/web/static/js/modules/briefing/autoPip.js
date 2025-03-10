/**
 * autoPip.js
 * Handles picture-in-picture functionality for video elements
 */

class AutoPip {
  constructor() {
    this.init();
  }

  init() {
    if (!this.checkFeatureSupport()) {
      return;
    }

    // Set up media session action handlers
    this.setupMediaSessionHandlers();
  }

  checkFeatureSupport() {
    if (!('mediaSession' in navigator)) {
      console.warn('MediaSession API not supported');
      return false;
    }

    if (!document.pictureInPictureEnabled) {
      console.warn('Picture-in-Picture API not supported');
      return false;
    }

    return true;
  }

  setupMediaSessionHandlers() {
    try {
      // Set metadata for media session
      navigator.mediaSession.metadata = new MediaMetadata({
        title: 'GeopolMonitor Briefing',
        artist: 'GeopolMonitor',
        artwork: [
          { src: '/static/images/logo.png', sizes: '96x96', type: 'image/png' }
        ]
      });

      // Set up picture-in-picture handler
      navigator.mediaSession.setActionHandler('enterpictureinpicture', () => {
        const video = document.querySelector('video');
        if (video && !document.pictureInPictureElement) {
          video.requestPictureInPicture().catch(error => {
            console.warn('Failed to enter Picture-in-Picture mode:', error);
          });
        }
      });

    } catch (error) {
      console.warn('Error setting up media session handlers:', error);
    }
  }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  new AutoPip();
});