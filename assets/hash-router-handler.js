/**
 * Hash router handler for managing search state in URL fragment.
 * Uses @techexp/hash-router library for routing without polling.
 * 
 * Hash format: #search/<base64-encoded-json>
 * JSON structure: { q: "query", ai: true/false }
 */

(function () {
    'use strict';

    if (typeof window === 'undefined') {
        return;
    }

    // Wait for DOM and Dash to be ready
    function initializeRouter() {
        let HashRouter;

        if (typeof window !== 'undefined' && window.HashRouter) {
            HashRouter = window.HashRouter;
        } else if (typeof require !== 'undefined') {
            try {
                HashRouter = require('@techexp/hash-router');
            } catch (e) {
                console.warn('Could not load hash-router via require');
            }
        }

        if (!HashRouter) {
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/@techexp/hash-router@0.3.0/dist/HashRouter-script-min.js';
            script.onload = function () {
                if (window.HashRouter) {
                    setupRouter(window.HashRouter);
                }
            };
            document.head.appendChild(script);
            return;
        }

        setupRouter(HashRouter);
    }

    function setupRouter(HashRouter) {
        const router = HashRouter.createRouter();

        /**
         * Encode search state to base64 string.
         * @param {string} query - Search query
         * @param {boolean} ai - AI search enabled
         * @returns {string} Base64 encoded JSON
         */
        function encodeState(query, ai) {
            if (!query || !query.trim()) {
                return '';
            }
            try {
                const state = { q: query.trim() };
                // Only include ai if it's false (default is true)
                if (ai === false) {
                    state.ai = false;
                }
                return btoa(JSON.stringify(state)).replace(/=+$/, '');
            } catch (e) {
                return '';
            }
        }

        /**
         * Decode base64 state string to object.
         * @param {string} encoded - Base64 encoded JSON
         * @returns {object} Decoded state { q: string, ai: boolean }
         */
        function decodeState(encoded) {
            if (!encoded) {
                return { q: '', ai: true };
            }
            try {
                const padding = 4 - (encoded.length % 4);
                const padded = padding !== 4 ? encoded + '='.repeat(padding) : encoded;
                const decoded = atob(padded);
                
                // Try to parse as JSON first (new format)
                try {
                    const state = JSON.parse(decoded);
                    return {
                        q: state.q || '',
                        ai: state.ai !== false  // Default to true
                    };
                } catch (jsonErr) {
                    // Fall back to old format (plain text query)
                    return { q: decoded, ai: true };
                }
            } catch (e) {
                return { q: '', ai: true };
            }
        }

        // Route handler for search query: search/:query
        router.add('search/:query', function (path, params) {
            // Hash router has already updated the hash, Dash's callback will pick it up
        });

        // Route handler for empty hash
        router.add('', function () {
            // Hash router has already updated the hash, Dash's callback will pick it up
        });

        /**
         * Update hash when search state changes.
         * Called from Dash clientside callback.
         * @param {string} query - Search query
         * @param {boolean} ai - AI search enabled
         */
        window.__updateHashFromState = function (query, ai) {
            const encoded = encodeState(query, ai);
            if (encoded) {
                window.location.href = '#search/' + encoded;
            } else {
                window.location.href = '#';
            }
        };

        // Legacy function for backward compatibility
        window.__updateHashFromQuery = function (query) {
            // Get current AI state from hash or default to true
            const currentState = decodeState(
                window.location.hash.startsWith('#search/') 
                    ? window.location.hash.substring(8) 
                    : ''
            );
            window.__updateHashFromState(query, currentState.ai);
        };

        /**
         * Decode current hash state.
         * Called from Dash clientside callback.
         * @returns {object} { q: string, ai: boolean }
         */
        window.__decodeHashState = function () {
            const hash = window.location.hash.substring(1);
            if (!hash || !hash.startsWith('search/')) {
                return { q: '', ai: true };
            }
            return decodeState(hash.substring(7));
        };

        window.__hashRouter = router;
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeRouter);
    } else {
        initializeRouter();
    }
})();
