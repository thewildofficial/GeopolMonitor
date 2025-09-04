/**
 * TierManager.js
 * Manages the interaction and display of briefing tiers (FLASH, SUMMARY, CONTEXT)
 */

class TierManager {
  constructor(options = {}) {
    // Store container references
    this.containers = {
      flash: options.flashContainer || null,
      summary: options.summaryContainer || null,
      context: options.contextContainer || null
    };
    
    // Track tier states
    this.tierStates = {
      flash: { collapsed: false },
      summary: { collapsed: false },
      context: { collapsed: false }
    };
    
    // Initialize the manager
    this.init();
  }
  
  /**
   * Initialize the tier manager
   */
  init() {
    this.setupEventListeners();
    this.setupInitialState();
  }
  
  /**
   * Set up event listeners for tier interactions
   */
  setupEventListeners() {
    // Add event listeners for tier toggle buttons
    document.addEventListener('click', (e) => {
      if (e.target.classList.contains('tier-toggle') || e.target.closest('.tier-toggle')) {
        const button = e.target.classList.contains('tier-toggle') ? e.target : e.target.closest('.tier-toggle');
        const targetId = button.getAttribute('data-target');
        
        if (targetId) {
          this.toggleTier(targetId);
        }
      }
    });
    
    // Add event listeners for panel toggle buttons
    document.addEventListener('click', (e) => {
      if (e.target.classList.contains('panel-toggle') || e.target.closest('.panel-toggle')) {
        const button = e.target.classList.contains('panel-toggle') ? e.target : e.target.closest('.panel-toggle');
        const targetId = button.getAttribute('data-target');
        
        if (targetId) {
          this.togglePanel(targetId);
        }
      }
    });
  }
  
  /**
   * Set up the initial state of tiers based on saved preferences or defaults
   */
  setupInitialState() {
    // Try to load saved state from localStorage
    try {
      const savedState = localStorage.getItem('briefingTierStates');
      if (savedState) {
        const parsedState = JSON.parse(savedState);
        
        // Apply saved states if they exist
        if (parsedState) {
          this.tierStates = { ...this.tierStates, ...parsedState };
          
          // Apply the saved states to the DOM
          for (const tier in this.tierStates) {
            if (this.tierStates[tier].collapsed) {
              const tierId = `${tier}Tier`;
              this.collapseTier(tierId, false); // Skip saving since we're just initializing
            }
          }
        }
      }
    } catch (error) {
      console.error('Error loading saved tier states:', error);
    }
  }
  
  /**
   * Toggle a tier's expanded/collapsed state
   * @param {string} tierId - The ID of the tier to toggle
   */
  toggleTier(tierId) {
    const tierElement = document.getElementById(tierId);
    const button = document.querySelector(`[data-target="${tierId}"]`);
    
    if (!tierElement || !button) return;
    
    const isCollapsed = tierElement.classList.contains('collapsed');
    
    if (isCollapsed) {
      this.expandTier(tierId);
    } else {
      this.collapseTier(tierId);
    }
  }
  
  /**
   * Collapse a tier
   * @param {string} tierId - The ID of the tier to collapse
   * @param {boolean} saveState - Whether to save the state change (default: true)
   */
  collapseTier(tierId, saveState = true) {
    const tierElement = document.getElementById(tierId);
    const button = document.querySelector(`[data-target="${tierId}"]`);
    const tierKey = tierId.replace('Tier', '').toLowerCase();
    
    if (!tierElement || !button) return;
    
    // Update DOM
    tierElement.classList.add('collapsed');
    tierElement.style.maxHeight = '0';
    button.classList.add('collapsed');
    
    // Update button icon
    const icon = button.querySelector('i');
    if (icon && icon.classList.contains('fa-chevron-up')) {
      icon.classList.remove('fa-chevron-up');
      icon.classList.add('fa-chevron-down');
    }
    
    // Update state
    this.tierStates[tierKey].collapsed = true;
    
    // Save state if requested
    if (saveState) {
      this.saveState();
    }
  }
  
  /**
   * Expand a tier
   * @param {string} tierId - The ID of the tier to expand
   * @param {boolean} saveState - Whether to save the state change (default: true)
   */
  expandTier(tierId, saveState = true) {
    const tierElement = document.getElementById(tierId);
    const button = document.querySelector(`[data-target="${tierId}"]`);
    const tierKey = tierId.replace('Tier', '').toLowerCase();
    
    if (!tierElement || !button) return;
    
    // Update DOM
    tierElement.classList.remove('collapsed');
    tierElement.style.maxHeight = tierElement.scrollHeight + 'px';
    button.classList.remove('collapsed');
    
    // Update button icon
    const icon = button.querySelector('i');
    if (icon && icon.classList.contains('fa-chevron-down')) {
      icon.classList.remove('fa-chevron-down');
      icon.classList.add('fa-chevron-up');
    }
    
    // Update state
    this.tierStates[tierKey].collapsed = false;
    
    // Save state if requested
    if (saveState) {
      this.saveState();
    }
  }
  
  /**
   * Toggle a panel's expanded/collapsed state
   * @param {string} panelId - The ID of the panel to toggle
   */
  togglePanel(panelId) {
    const panelElement = document.getElementById(panelId);
    const button = document.querySelector(`[data-target="${panelId}"]`);
    
    if (!panelElement || !button) return;
    
    const isCollapsed = panelElement.classList.contains('collapsed');
    
    if (isCollapsed) {
      this.expandPanel(panelId);
    } else {
      this.collapsePanel(panelId);
    }
  }
  
  /**
   * Collapse a panel
   * @param {string} panelId - The ID of the panel to collapse
   */
  collapsePanel(panelId) {
    const panelElement = document.getElementById(panelId);
    const button = document.querySelector(`[data-target="${panelId}"]`);
    
    if (!panelElement || !button) return;
    
    // Update DOM
    panelElement.classList.add('collapsed');
    panelElement.style.maxHeight = '0';
    button.classList.add('collapsed');
    
    // Update button icon
    const icon = button.querySelector('i');
    if (icon && icon.classList.contains('fa-chevron-up')) {
      icon.classList.remove('fa-chevron-up');
      icon.classList.add('fa-chevron-down');
    }
  }
  
  /**
   * Expand a panel
   * @param {string} panelId - The ID of the panel to expand
   */
  expandPanel(panelId) {
    const panelElement = document.getElementById(panelId);
    const button = document.querySelector(`[data-target="${panelId}"]`);
    
    if (!panelElement || !button) return;
    
    // Update DOM
    panelElement.classList.remove('collapsed');
    panelElement.style.maxHeight = panelElement.scrollHeight + 'px';
    button.classList.remove('collapsed');
    
    // Update button icon
    const icon = button.querySelector('i');
    if (icon && icon.classList.contains('fa-chevron-down')) {
      icon.classList.remove('fa-chevron-down');
      icon.classList.add('fa-chevron-up');
    }
  }
  
  /**
   * Save the current tier states to localStorage
   */
  saveState() {
    try {
      localStorage.setItem('briefingTierStates', JSON.stringify(this.tierStates));
    } catch (error) {
      console.error('Error saving tier states:', error);
    }
  }
  
  /**
   * Check if a tier is collapsed
   * @param {string} tierKey - The key of the tier to check (flash, summary, context)
   * @returns {boolean} Whether the tier is collapsed
   */
  isTierCollapsed(tierKey) {
    return this.tierStates[tierKey]?.collapsed || false;
  }
  
  /**
   * Expand all tiers
   */
  expandAllTiers() {
    this.expandTier('flashTier');
    this.expandTier('summaryTier');
    this.expandTier('contextTier');
  }
  
  /**
   * Collapse all tiers
   */
  collapseAllTiers() {
    this.collapseTier('flashTier');
    this.collapseTier('summaryTier');
    this.collapseTier('contextTier');
  }
  
  /**
   * Animate updates to specific tier content
   * @param {string} tierId - ID of the tier being updated
   * @param {HTMLElement} itemElement - The element to highlight as updated
   */
  highlightUpdate(tierId, itemElement) {
    if (!itemElement) return;
    
    // Add highlight animation class
    itemElement.classList.add('updated');
    
    // Expand tier if it was collapsed
    const tierKey = tierId.replace('Tier', '').toLowerCase();
    if (this.isTierCollapsed(tierKey)) {
      this.expandTier(tierId);
    }
    
    // Remove highlight class after animation completes
    setTimeout(() => {
      itemElement.classList.remove('updated');
    }, 3000);
  }
}