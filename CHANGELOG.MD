# Changelog

## [Unreleased] – 2024-2-16

### Major Map Interface Revamp
- **Country News Panel:** Implemented a floating panel that displays country-specific news when clicking on a country
- **Enhanced UI:** Improved map interface with Apple-style floating window design and better visual hierarchy
- **Theme Integration:** Refined dark/light mode handling for the news panel with proper contrast and readability
- **Performance:** Added comprehensive country name matching and emoji-based detection for better news filtering
- **Country Detection:** Improved country name normalization and mapping for more accurate news association
- **Error Handling:** Added debug mode and logging for better troubleshooting of country-news associations

### Visual Improvements
- **Panel Design:** Added sleek floating panel design with backdrop blur and smooth animations
- **Contrast:** Enhanced text readability with better background opacity and contrast ratios
- **Mobile Responsiveness:** Improved mobile view with bottom sheet design for country news
- **Map Attribution:** Removed map attribution for cleaner interface
- **Country Highlights:** Added pulsing highlight effect for selected countries

## [Unreleased] – 2024-2-13

### Map Updates (In Progress)
- **Theme Switching:** Improved the theme observer in [src/web/static/js/map-page.js](src/web/static/js/map-page.js) to better handle dark/light mode transitions by switching tile layers dynamically.
- **Heatmap Adjustments:** Enhanced the heatmap gradient in [src/web/static/js/map-page.js](src/web/static/js/map-page.js) for subtler colors and more intuitive visualization.
- **Timeline Slider:** Integrated a timeline slider for filtering news by days (see [src/web/static/js/map-page.js](src/web/static/js/map-page.js) and [src/web/static/js/modules/map.js](src/web/static/js/modules/map.js)) to allow users to dynamically view historical news distribution.
- **Responsive Design:** Updated [src/web/static/css/modules/map.css](src/web/static/css/modules/map.css) to ensure better mobile responsiveness and a cohesive style across different screen sizes.

### Tagging System Enhancements
- **Automatic Tagging Introduction:** Added initial support for an automatic content tagging system. A new module (referenced in [`src/web/static/js/modules/tags.js`](src/web/static/js/modules/tags.js)) now provides helper functions to extract and manage tags.
- **Active Tags API:** Integrated the `getActiveTags` function (from [`src/web/static/js/modules/tags.js`](src/web/static/js/modules/tags.js)) into the map update workflow in [src/web/static/js/modules/map.js](src/web/static/js/modules/map.js) to filter and highlight news based on tags.
- **Preliminary Filtering:** Enabled preliminary tag-based filtering on news items for improved contextual relevance on the map view.

*Note: Map changes are still in progress, and further adjustments are expected as the integration with real-time data and user feedback continues.*