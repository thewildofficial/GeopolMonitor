// Utility to map region/country names to flag emojis for UI display

const NAME_TO_FLAG: Record<string, string> = {
  // Common countries/regions we expect in demo and real data
  "United States": "🇺🇸",
  "USA": "🇺🇸",
  "US": "🇺🇸",
  "United Kingdom": "🇬🇧",
  "UK": "🇬🇧",
  "Britain": "🇬🇧",
  "Germany": "🇩🇪",
  "France": "🇫🇷",
  "Italy": "🇮🇹",
  "Spain": "🇪🇸",
  "Russia": "🇷🇺",
  "Ukraine": "🇺🇦",
  "China": "🇨🇳",
  "Japan": "🇯🇵",
  "South Korea": "🇰🇷",
  "North Korea": "🇰🇵",
  "India": "🇮🇳",
  "Pakistan": "🇵🇰",
  "Israel": "🇮🇱",
  "Palestine": "🇵🇸",
  "Iran": "🇮🇷",
  "Iraq": "🇮🇶",
  "Syria": "🇸🇾",
  "Turkey": "🇹🇷",
  "Saudi Arabia": "🇸🇦",
  "United Arab Emirates": "🇦🇪",
  "Qatar": "🇶🇦",
  "Lebanon": "🇱🇧",
  "Jordan": "🇯🇴",
  "Egypt": "🇪🇬",
  "Canada": "🇨🇦",
  "Mexico": "🇲🇽",
  "Brazil": "🇧🇷",
  "Argentina": "🇦🇷",
  "Australia": "🇦🇺",
  "New Zealand": "🇳🇿",
  "Nigeria": "🇳🇬",
  "South Africa": "🇿🇦",
  // Blocs/regions
  "European Union": "🇪🇺",
  "Europe": "🇪🇺",
  "Global": "🌐",
  "Middle East": "🧭",
  "Asia": "🌏",
  "Africa": "🌍",
  "Americas": "🌎",
};

// If an ISO 3166-1 alpha-2 code is provided, convert to flag
function isoToFlag(iso: string): string | null {
  if (!iso || iso.length !== 2) return null;
  const code = iso.toUpperCase();
  const A = 127462; // regional indicator symbol letter A
  const first = code.charCodeAt(0) - 65 + A;
  const second = code.charCodeAt(1) - 65 + A;
  if (first < A || second < A) return null;
  return String.fromCodePoint(first) + String.fromCodePoint(second);
}

export function getFlagEmoji(nameOrCode?: string): string {
  if (!nameOrCode) return "";
  const key = nameOrCode.trim();
  // Exact mapping first
  if (NAME_TO_FLAG[key]) return NAME_TO_FLAG[key];
  // Try ISO code
  if (key.length === 2) {
    const flag = isoToFlag(key);
    if (flag) return flag;
  }
  // Try title-case match by splitting commas (e.g., "Berlin, Germany")
  const parts = key.split(",").map((p) => p.trim());
  for (const part of parts) {
    if (NAME_TO_FLAG[part]) return NAME_TO_FLAG[part];
  }
  return ""; // fallback to no flag
}


