/**
 * Hash router handler for managing search query in URL fragment.
 * Uses @techexp/hash-router library for routing without polling.
 */

(function () {
    'use strict';

    if (typeof window === 'undefined') {
        return;
    }

    // Wait for DOM and Dash to be ready
    function initializeRouter() {
        // Try to get HashRouter from window (loaded via script tag or CDN)
        // If using npm package, it should be available as window.HashRouter or via import
        let HashRouter;

        if (typeof window !== 'undefined' && window.HashRouter) {
            HashRouter = window.HashRouter;
        } else if (typeof require !== 'undefined') {
            // Try CommonJS require (for Node/bundled environments)
            try {
                HashRouter = require('@techexp/hash-router');
            } catch (e) {
                console.warn('Could not load hash-router via require');
            }
        }

        if (!HashRouter) {
            // Load from CDN as fallback
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
        // Create router instance
        const router = HashRouter.createRouter();

        // Base64 encode/decode helpers
        function encodeQuery(query) {
            if (!query || !query.trim()) {
                return '';
            }
            try {
                return btoa(query.trim()).replace(/=+$/, '');
            } catch (e) {
                return '';
            }
        }

        function decodeQuery(encoded) {
            if (!encoded) {
                return '';
            }
            try {
                const padding = 4 - (encoded.length % 4);
                const padded = padding !== 4 ? encoded + '='.repeat(padding) : encoded;
                return atob(padded);
            } catch (e) {
                return '';
            }
        }

        // Route handler for search query: search/:query
        // Note: We don't directly update Dash components here. Instead, we let Dash's
        // callback listening to url.hash handle the update. This prevents errors from
        // calling set_props before Dash is ready.
        router.add('search/:query', function (path, params) {
            // Hash router has already updated the hash, so Dash's callback will pick it up
            // No need to manually update the search input here
        });

        // Route handler for empty hash (no search)
        router.add('', function () {
            // Hash router has already updated the hash, so Dash's callback will pick it up
            // No need to manually update the search input here
        });

        // Function to update hash when search query changes (called from Dash callback)
        window.__updateHashFromQuery = function (query) {
            const encoded = encodeQuery(query);
            if (encoded) {
                window.location.href = '#search/' + encoded;
            } else {
                window.location.href = '#';
            }
        };

        // Store router for external access
        window.__hashRouter = router;

        // Hash-router automatically handles hash changes, including initial load
        // No need to manually navigate - the router listens to hashchange events
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeRouter);
    } else {
        // DOM already loaded
        initializeRouter();
    }
})();

