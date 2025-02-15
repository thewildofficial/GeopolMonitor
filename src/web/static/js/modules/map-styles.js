// Map styling and color utilities
export const mapStyles = {
    colors: {
        light: {
            low: 'rgba(52, 152, 219, 0.2)',     // Light blue
            mediumLow: 'rgba(52, 152, 219, 0.4)', // Medium blue
            medium: 'rgba(52, 152, 219, 0.6)',    // Darker blue
            mediumHigh: 'rgba(52, 152, 219, 0.8)', // Even darker blue
            high: 'rgba(52, 152, 219, 1.0)'       // Full blue
        },
        dark: {
            low: 'rgba(64, 115, 255, 0.25)',     // Bright glow
            mediumLow: 'rgba(64, 115, 255, 0.45)', // Brighter glow
            medium: 'rgba(64, 115, 255, 0.65)',    // Strong glow
            mediumHigh: 'rgba(64, 115, 255, 0.85)', // Very strong glow
            high: 'rgba(64, 115, 255, 1.0)'       // Full glow
        }
    },

    getColorPalette() {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        return this.colors[isDark ? 'dark' : 'light'];
    },

    getCountryStyle(heatData, maxCount) {
        if (!heatData || !heatData.count) {
            return {
                fillColor: 'transparent',
                fillOpacity: 0.1,
                weight: 1,
                color: 'var(--border-color)',
                opacity: 0.3,
                className: 'country-inactive'
            };
        }

        const normalizedCount = heatData.count / maxCount;
        const colors = this.getColorPalette();
        
        // Calculate color based on normalized count with smoother transitions
        let fillColor;
        if (normalizedCount < 0.2) {
            fillColor = this.interpolateColor(colors.low, colors.mediumLow, normalizedCount * 5);
        } else if (normalizedCount < 0.4) {
            fillColor = this.interpolateColor(colors.mediumLow, colors.medium, (normalizedCount - 0.2) * 5);
        } else if (normalizedCount < 0.6) {
            fillColor = this.interpolateColor(colors.medium, colors.mediumHigh, (normalizedCount - 0.4) * 5);
        } else if (normalizedCount < 0.8) {
            fillColor = this.interpolateColor(colors.mediumHigh, colors.high, (normalizedCount - 0.6) * 5);
        } else {
            fillColor = colors.high;
        }

        // Increase the base opacity range
        const baseOpacity = 0.4;
        const maxOpacity = 1.0;
        const fillOpacity = baseOpacity + (normalizedCount * (maxOpacity - baseOpacity));

        return {
            fillColor,
            fillOpacity,
            weight: 1,
            color: 'var(--border-color)',
            opacity: 0.5,
            className: 'country-active'
        };
    },

    interpolateColor(color1, color2, factor) {
        const c1 = this.parseRgba(color1);
        const c2 = this.parseRgba(color2);
        
        return `rgba(${
            Math.round(c1.r + (c2.r - c1.r) * factor)
        }, ${
            Math.round(c1.g + (c2.g - c1.g) * factor)
        }, ${
            Math.round(c1.b + (c2.b - c1.b) * factor)
        }, ${
            c1.a + (c2.a - c1.a) * factor
        })`;
    },

    parseRgba(color) {
        const match = color.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*(\d*\.?\d+))?\)/);
        return match ? {
            r: parseInt(match[1]),
            g: parseInt(match[2]),
            b: parseInt(match[3]),
            a: match[4] ? parseFloat(match[4]) : 1
        } : null;
    },

    getLegendGradient() {
        const colors = this.getColorPalette();
        return `linear-gradient(to right,
            ${colors.low},
            ${colors.mediumLow},
            ${colors.medium},
            ${colors.mediumHigh},
            ${colors.high}
        )`;
    },

    getActiveCountryStyle() {
        return {
            weight: 2,
            color: 'var(--accent-color)',
            opacity: 1,
            fillOpacity: 0.4,
            fillColor: 'var(--accent-color)',
            className: 'country-highlight'
        };
    },

    getHoverStyle(baseStyle) {
        return {
            ...baseStyle,
            weight: 2,
            color: 'var(--accent-color)',
            opacity: 0.8,
            fillOpacity: Math.min(1, (baseStyle.fillOpacity || 0) * 1.3),
            className: 'country-hover'
        };
    }
};