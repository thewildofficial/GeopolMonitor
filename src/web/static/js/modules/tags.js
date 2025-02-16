import { normalizeCountry } from './countries.js';

let activeTags = new Set();
let relatedTags = new Map();

export async function loadTags() {
    try {
        const response = await fetch('/api/tags');
        const tags = await response.json();
        
        const sourceContainer = document.getElementById('sourceTags');
        const topicContainer = document.getElementById('topicTags');
        const geoContainer = document.getElementById('geographyTags');
        const eventContainer = document.getElementById('eventTags');
        
        // Clear existing tags
        sourceContainer.innerHTML = '';
        topicContainer.innerHTML = '';
        geoContainer.innerHTML = '';
        eventContainer.innerHTML = '';
        
        // Store all tags for searching and build relationships
        window.allTags = {
            source: tags.source || [],
            topic: tags.topic || [],
            geography: tags.geography || [],
            events: tags.events || []
        };

        // Build tag relationships based on co-occurrence in articles
        buildTagRelationships();
        
        // Initialize tag search and render
        const tagSearch = document.getElementById('tagSearch');
        tagSearch.addEventListener('input', (e) => {
            renderTags(e.target.value);
        });
        
        renderTags();
        updateFilterCount();
    } catch (error) {
        console.error('Error loading tags:', error);
    }
}

async function buildTagRelationships() {
    try {
        const response = await fetch('/api/news');
        const { news } = await response.json();
        
        relatedTags.clear();
        
        // Build relationships based on co-occurrence
        news.forEach(item => {
            if (!item.tags) return;
            
            item.tags.forEach(tag1 => {
                item.tags.forEach(tag2 => {
                    if (tag1.name === tag2.name) return;
                    
                    const key1 = tag1.name;
                    if (!relatedTags.has(key1)) {
                        relatedTags.set(key1, new Map());
                    }
                    
                    const relationMap = relatedTags.get(key1);
                    relationMap.set(tag2.name, (relationMap.get(tag2.name) || 0) + 1);
                });
            });
        });
    } catch (error) {
        console.error('Error building tag relationships:', error);
    }
}

function highlightRelatedTags(tagName, highlight = true) {
    const related = relatedTags.get(tagName);
    if (!related) return;
    
    document.querySelectorAll('.tag').forEach(tag => {
        if (related.has(tag.dataset.tagName)) {
            const strength = related.get(tag.dataset.tagName);
            if (highlight) {
                tag.style.opacity = '1';
                tag.style.transform = `scale(${1 + Math.min(strength / 10, 0.1)})`;
                tag.style.borderColor = 'var(--accent-color)';
            } else {
                tag.style.opacity = '';
                tag.style.transform = '';
                tag.style.borderColor = '';
            }
        }
    });
}

function createTag(name, count, category) {
    const tag = document.createElement('span');
    tag.className = 'tag';
    tag.dataset.category = category;
    
    // Format display name with emoji for geography tags
    if (category === 'geography') {
        const countryData = normalizeCountry(name);
        const normalizedName = countryData.name;
        const flag = countryData.flag || '';
        
        // Store both flag and name separately for consistent access
        tag.dataset.tagName = normalizedName;
        tag.dataset.flag = flag;
        tag.dataset.displayName = `${flag} ${normalizedName}`;
        
        // Create tag content with flag
        tag.innerHTML = `${flag} ${normalizedName}`;
    } else {
        tag.textContent = name;
        tag.dataset.tagName = name;
        tag.dataset.displayName = name;
    }
    
    // Add count
    const countSpan = document.createElement('span');
    countSpan.className = 'count';
    countSpan.textContent = count;
    tag.appendChild(countSpan);
    
    // Add hover effect to show related tags
    tag.addEventListener('mouseenter', () => {
        highlightRelatedTags(tag.dataset.tagName, true);
    });
    
    tag.addEventListener('mouseleave', () => {
        if (!tag.classList.contains('active')) {
            highlightRelatedTags(tag.dataset.tagName, false);
        }
    });
    
    tag.addEventListener('click', () => {
        tag.classList.toggle('active');
        if (tag.classList.contains('active')) {
            addTag(tag.dataset.tagName);
            highlightRelatedTags(tag.dataset.tagName, true);
        } else {
            removeTag(tag.dataset.tagName);
            highlightRelatedTags(tag.dataset.tagName, false);
        }
        window.updateNews();
    });
    
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

    // Helper function to merge duplicate tags and their counts
    function mergeDuplicates(tags) {
        const mergedMap = new Map();
        
        tags.forEach(tag => {
            let key = tag.name;
            if (key) {
                // For geography tags, normalize the country name
                if (tag.category === 'geography') {
                    key = normalizeCountry(tag.name).name;
                }
                
                if (mergedMap.has(key)) {
                    mergedMap.set(key, {
                        name: key,
                        count: mergedMap.get(key).count + tag.count,
                        category: tag.category
                    });
                } else {
                    mergedMap.set(key, {
                        name: key,
                        count: tag.count,
                        category: tag.category
                    });
                }
            }
        });
        
        return Array.from(mergedMap.values());
    }
    
    if (window.allTags.source) {
        const filteredSource = mergeDuplicates(window.allTags.source.map(t => ({...t, category: 'source'})))
            .sort((a, b) => b.count - a.count)
            .filter(tag => tag.name.toLowerCase().includes(searchLower));
        
        filteredSource.forEach(tag => {
            sourceContainer.appendChild(createTag(tag.name, tag.count, 'source'));
        });
        sourceContainer.closest('.tag-section').style.display = 
            filteredSource.length ? 'block' : 'none';
    }
    
    if (window.allTags.topic) {
        const filteredTopic = mergeDuplicates(window.allTags.topic.map(t => ({...t, category: 'topic'})))
            .sort((a, b) => b.count - a.count)
            .filter(tag => tag.name.toLowerCase().includes(searchLower));
        
        filteredTopic.forEach(tag => {
            topicContainer.appendChild(createTag(tag.name, tag.count, 'topic'));
        });
        topicContainer.closest('.tag-section').style.display = 
            filteredTopic.length ? 'block' : 'none';
    }
    
    if (window.allTags.geography) {
        const filteredGeo = mergeDuplicates(window.allTags.geography.map(t => ({...t, category: 'geography'})))
            .sort((a, b) => b.count - a.count)
            .filter(tag => {
                const countryData = normalizeCountry(tag.name);
                const searchText = [
                    countryData.name.toLowerCase(),
                    countryData.flag || '',
                    tag.name.toLowerCase(),
                    tag.name.replace(/-/g, ' ').toLowerCase()
                ].join(' ');
                return searchText.includes(searchLower);
            });
        
        // Log geography tags sorted by count
        console.log('Geography tags by count:', 
            filteredGeo.map(tag => {
                const countryData = normalizeCountry(tag.name);
                return {
                    name: `${countryData.flag || ''} ${countryData.name}`,
                    count: tag.count
                };
            })
        );
        
        filteredGeo.forEach(tag => {
            geoContainer.appendChild(createTag(tag.name, tag.count, 'geography'));
        });
        geoContainer.closest('.tag-section').style.display = 
            filteredGeo.length ? 'block' : 'none';
    }
    
    if (window.allTags.events) {
        const filteredEvents = mergeDuplicates(window.allTags.events.map(t => ({...t, category: 'events'})))
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
    const countryData = normalizeCountry(tagName);
    const normalizedTagName = countryData.name;
    
    if (activeTags.has(normalizedTagName)) {
        activeTags.delete(normalizedTagName);
    } else {
        activeTags.add(normalizedTagName);
    }
    updateFilterCount();
    
    // Update tag visual states
    document.querySelectorAll('.tag').forEach(tag => {
        if (tag.dataset.tagName === normalizedTagName) {
            tag.classList.toggle('active');
        }
    });
    
    // Update news list with new filter
    window.updateNews();
};

export async function updateNews() {
    try {
        const activeTags = getActiveTags();
        const tagParam = activeTags.length > 0 ? `?tags=${activeTags.join(',')}` : '';
        const news = await fetchNews();
        if (!news || news.length === 0) return;
        
        const filtered = await filterNews(news);
        filtered.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
        
        // Update visual state of tag filter button
        const filterToggle = document.getElementById('filterToggle');
        filterToggle.classList.toggle('has-active-filters', activeTags.length > 0);

        // Animate filtering
        const container = document.getElementById('newsContainer');
        const currentItems = Array.from(container.children);
        
        // First mark items that should be filtered out
        currentItems.forEach(item => {
            const shouldShow = filtered.some(news => {
                const itemLink = item.querySelector('article').onclick.toString().match(/'([^']+)'/)[1];
                return news.link === itemLink;
            });
            
            if (!shouldShow) {
                item.classList.add('filtered-out');
            }
        });

        // Wait for fade out animation
        await new Promise(resolve => setTimeout(resolve, 300));

        // Update the news list
        await updateNewsList(filtered);

        // Add filtered-in class to new items for animation
        container.querySelectorAll('.news-item').forEach(item => {
            item.classList.add('filtered-in');
        });
        
        lastUpdate = new Date();
    } catch (error) {
        console.error('Error updating news:', error);
    }
}

// Format the tag name consistently
export function formatTagName(name) {
    return name.toLowerCase().split(' ').map(word => 
        word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
}

function addTag(name) {
    activeTags.add(name);
    updateFilterCount();
}

function removeTag(name) {
    activeTags.delete(name);
    updateFilterCount();
}

export function getActiveTags() {
    return Array.from(activeTags);
}

function updateFilterCount() {
    const filterCount = document.querySelector('.filter-count');
    const count = activeTags.size;
    filterCount.textContent = count || '';
    filterCount.classList.toggle('active', count > 0);
}

export function toggleTagFilters() {
    const tagFilters = document.querySelector('.tag-filters');
    tagFilters.classList.toggle('collapsed');
}

function formatTagDisplayName(name, category) {
    if (category === 'geography') {
        const countryData = normalizeCountry(name);
        return `${countryData.flag || ''} ${countryData.name}`;
    }
    return name;
}