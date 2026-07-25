/**
 * DataForge — Theme & Typography Switcher
 * Manages UI themes and font sets dynamically.
 */

const ThemeManager = {
    // List of available themes with metadata for customization panels
    themes: [
        { id: 'dark', name: 'Dark Default', isDark: true, preview: ['#050505', '#0A0A0B', '#2E5BFF'] },
        { id: 'light', name: 'Light Default', isDark: false, preview: ['#f8fafc', '#ffffff', '#4f46e5'] },
        { id: 'dracula', name: 'Dracula', isDark: true, preview: ['#282a36', '#1e1f29', '#bd93f9'] },
        { id: 'slate', name: 'Slate Blue', isDark: true, preview: ['#1e222b', '#252a34', '#38bdf8'] },
        { id: 'emerald', name: 'Emerald Sage', isDark: true, preview: ['#141e1b', '#1b2824', '#10b981'] },
        { id: 'nord', name: 'Nord', isDark: true, preview: ['#2e3440', '#3b4252', '#88c0d0'] },
        { id: 'luxury', name: 'Luxury', isDark: true, preview: ['#09090b', '#18181b', '#d4af37'] },
        { id: 'cupcake', name: 'Cupcake', isDark: false, preview: ['#fafaf9', '#ffffff', '#ec4899'] },
        { id: 'solarized', name: 'Solarized Light', isDark: false, preview: ['#fdf6e3', '#eee8d5', '#2aa198'] },
        { id: 'lavender', name: 'Lavender Mint', isDark: false, preview: ['#f5f3ff', '#ffffff', '#7c3aed'] },
        { id: 'matcha', name: 'Mint Matcha', isDark: false, preview: ['#f4f8f5', '#ffffff', '#15803d'] }
    ],

    // List of fonts
    fonts: [
        { id: 'inter', name: 'Inter (Standard)' },
        { id: 'outfit', name: 'Outfit (Geometric)' },
        { id: 'poppins', name: 'Poppins (Friendly)' },
        { id: 'roboto-mono', name: 'Roboto Mono' },
        { id: 'playfair', name: 'Playfair Display' },
        { id: 'rajdhani', name: 'Rajdhani (Futuristic)' }
    ],

    // Default font pairs for specific themes
    defaultFonts: {
        slate: 'outfit',
        emerald: 'poppins',
        luxury: 'playfair',
        dracula: 'roboto-mono',
        nord: 'outfit',
        cupcake: 'poppins',
        solarized: 'inter',
        lavender: 'poppins',
        matcha: 'outfit',
        dark: 'inter',
        light: 'inter'
    },

    getTheme() {
        try {
            return localStorage.getItem('analyst-theme') || 'light';
        } catch (e) {
            return 'light';
        }
    },

    getFont() {
        try {
            return localStorage.getItem('analyst-font') || 'inter';
        } catch (e) {
            return 'inter';
        }
    },

    // Apply theme + font settings to document
    apply(themeId, fontId) {
        const root = document.getElementById('html-root') || document.documentElement;
        if (!root) return;

        root.setAttribute('data-theme', themeId);
        root.setAttribute('data-font', fontId);

        // Keep legacy backward compatibility with light class toggle
        const theme = this.themes.find(t => t.id === themeId);
        const isDark = theme ? theme.isDark : true;
        if (isDark) {
            root.classList.remove('light');
        } else {
            root.classList.add('light');
        }

        // Broadcast to dynamic iframes
        this.notifyIframes(themeId);
    },

    // Set theme and save preference
    setTheme(themeId) {
        const previousTheme = this.getTheme();
        try {
            localStorage.setItem('analyst-theme', themeId);
        } catch (e) {
            console.warn('localStorage is not accessible:', e);
        }
        
        // Auto pairing: update font only if the user hasn't overridden it, 
        // or if they are switching to a highly styled theme (Luxury, Dracula)
        let fontId = this.getFont();
        const defaultPair = this.defaultFonts[themeId];
        if (defaultPair && (themeId === 'luxury' || themeId === 'dracula' || fontId === this.defaultFonts[previousTheme])) {
            try {
                localStorage.setItem('analyst-font', defaultPair);
            } catch (e) {}
            fontId = defaultPair;
        }

        this.apply(themeId, fontId);
        this.refreshIframes(themeId);
    },

    // Set font and save preference
    setFont(fontId) {
        try {
            localStorage.setItem('analyst-font', fontId);
        } catch (e) {}
        const currentTheme = this.getTheme();
        this.apply(currentTheme, fontId);
    },

    // Broadcast active theme via postMessage to nested frames
    notifyIframes(themeId) {
        const theme = this.themes.find(t => t.id === themeId);
        const isDark = theme ? theme.isDark : true;
        const mappedTheme = isDark ? 'dark' : 'light';

        document.querySelectorAll('iframe').forEach(iframe => {
            try {
                iframe.contentWindow.postMessage({
                    type: 'set-theme',
                    theme: themeId
                }, '*');
            } catch (e) {
                // Ignore cross-origin warnings
            }
        });
    },

    // Force refresh of backend-rendered frames with active theme parameter
    refreshIframes(themeId) {
        const theme = this.themes.find(t => t.id === themeId);
        const isDark = theme ? theme.isDark : true;
        const mappedTheme = isDark ? 'dark' : 'light';

        const edaFrame = document.getElementById('eda-frame');
        if (edaFrame && edaFrame.src && edaFrame.src.includes('/api/eda/report')) {
            const url = new URL(edaFrame.src);
            url.searchParams.set('theme', themeId);
            url.searchParams.set('t', Date.now());
            edaFrame.src = url.toString();
        }

        const rf = document.getElementById('report-frame');
        if (rf && rf.src && rf.src.includes('/api/reports/')) {
            const url = new URL(rf.src);
            url.searchParams.set('theme', mappedTheme);
            url.searchParams.set('t', Date.now());
            rf.src = url.toString();
        }
    },

    // Auto initialize variables
    init() {
        const theme = this.getTheme();
        const font = this.getFont();
        this.apply(theme, font);
    }
};

// Immediate execution to prevent theme flashes
ThemeManager.init();
document.addEventListener('DOMContentLoaded', () => ThemeManager.init());
window.ThemeManager = ThemeManager;
