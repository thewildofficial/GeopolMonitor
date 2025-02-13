let activeTags = new Set();

export async function loadTags() {
    try {
        const response = await fetch('/api/tags');
        const tags = await response.json();
        
        const sourceContainer = document.getElementById('sourceTags');
        const topicContainer = document.getElementById('topicTags');
        const geoContainer = document.getElementById('geographyTags');
        const eventContainer = document.getElementById('eventTags');
        const tagSearch = document.getElementById('tagSearch');
        
        // Clear existing tags
        sourceContainer.innerHTML = '';
        topicContainer.innerHTML = '';
        geoContainer.innerHTML = '';
        eventContainer.innerHTML = '';
        
        // Store all tags for searching
        window.allTags = {
            source: tags.source || [],
            topic: tags.topic || [],
            geography: tags.geography || [],
            events: tags.events || []
        };
        
        // Initialize tag search and render
        tagSearch.addEventListener('input', (e) => {
            renderTags(e.target.value);
        });
        
        renderTags();
        updateFilterCount();
    } catch (error) {
        console.error('Error loading tags:', error);
    }
}

export function updateFilterCount() {
    const filterCount = document.querySelector('.filter-count');
    const filterToggle = document.getElementById('filterToggle');
    
    if (activeTags.size > 0) {
        filterCount.textContent = activeTags.size;
        filterCount.classList.add('active');
        filterToggle.classList.add('has-active-filters');
    } else {
        filterCount.textContent = '';
        filterCount.classList.remove('active');
        filterToggle.classList.remove('has-active-filters');
    }
}

export function toggleTagFilters() {
    const tagFilters = document.querySelector('.tag-filters');
    const wasCollapsed = tagFilters.classList.contains('collapsed');
    
    tagFilters.classList.toggle('collapsed');
    
    if (wasCollapsed) {
        const tagSearch = document.getElementById('tagSearch');
        tagSearch.focus();
    }
}

export function getActiveTags() {
    return Array.from(activeTags);
}

export function addTag(tag) {
    activeTags.add(tag);
    updateFilterCount();
}

export function removeTag(tag) {
    activeTags.delete(tag);
    updateFilterCount();
}

function createTag(name, count, category) {
    const tag = document.createElement('span');
    tag.className = 'tag';
    tag.innerHTML = `${name} <span class="count">${count}</span>`;
    tag.dataset.tagName = name;
    tag.dataset.category = category;
    
    tag.addEventListener('click', () => {
        tag.classList.toggle('active');
        if (tag.classList.contains('active')) {
            addTag(name);
        } else {
            removeTag(name);
        }
        window.updateNews();
    });
    
    tag.title = name;
    return tag;
}

function renderTags(searchTerm = '') {
    const sourceContainer = document.getElementById('sourceTags');
    const topicContainer = document.getElementById('topicTags');
    const geoContainer = document.getElementById('geographyTags');
    const eventContainer = document.getElementById('eventTags');
    
    [sourceContainer, topicContainer, geoContainer, eventContainer].forEach(container => {
        container.innerHTML = '';
    });
    
    const searchLower = searchTerm.toLowerCase();
    
    if (window.allTags.source) {
        const filteredSource = window.allTags.source
            .sort((a, b) => b.count - a.count)
            .filter(tag => tag.name.toLowerCase().includes(searchLower));
        
        filteredSource.forEach(tag => {
            sourceContainer.appendChild(createTag(tag.name, tag.count, 'source'));
        });
        sourceContainer.closest('.tag-section').style.display = 
            filteredSource.length ? 'block' : 'none';
    }
    
    if (window.allTags.topic) {
        const filteredTopic = window.allTags.topic
            .sort((a, b) => b.count - a.count)
            .filter(tag => tag.name.toLowerCase().includes(searchLower));
        
        filteredTopic.forEach(tag => {
            topicContainer.appendChild(createTag(tag.name, tag.count, 'topic'));
        });
        topicContainer.closest('.tag-section').style.display = 
            filteredTopic.length ? 'block' : 'none';
    }
    
    if (window.allTags.geography) {
        const filteredGeo = window.allTags.geography
            .sort((a, b) => b.count - a.count)
            .filter(tag => tag.name.toLowerCase().includes(searchLower));
        
        filteredGeo.forEach(tag => {
            geoContainer.appendChild(createTag(tag.name, tag.count, 'geography'));
        });
        geoContainer.closest('.tag-section').style.display = 
            filteredGeo.length ? 'block' : 'none';
    }
    
    if (window.allTags.events) {
        const filteredEvents = window.allTags.events
            .sort((a, b) => b.count - a.count)
            .filter(tag => tag.name.toLowerCase().includes(searchLower));
        
        filteredEvents.forEach(tag => {
            eventContainer.appendChild(createTag(tag.name, tag.count, 'events'));
        });
        eventContainer.closest('.tag-section').style.display = 
            filteredEvents.length ? 'block' : 'none';
    }
    
    // Restore active state for selected tags
    document.querySelectorAll('.tag').forEach(tag => {
        if (activeTags.has(tag.dataset.tagName)) {
            tag.classList.add('active');
        }
    });
}

// Make toggleTag available globally
window.toggleTag = (tagName) => {
    if (activeTags.has(tagName)) {
        activeTags.delete(tagName);
    } else {
        activeTags.add(tagName);
    }
    updateFilterCount();
    
    // Update tag visual states
    document.querySelectorAll('.tag').forEach(tag => {
        if (tag.textContent === tagName) {
            tag.classList.toggle('active');
        }
    });
    
    // Update news list with new filter
    window.updateNews();
};