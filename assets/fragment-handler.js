/**
 * Fragment handler for reading and writing search queries in the URI fragment.
 * Uses format: #search=base64encodedquery
 */

// Initialize fragment handler on window load
(function() {
    'use strict';
    
    if (typeof window === 'undefined') {
        return;
    }
    
    // Initialize fragment handler singleton
    if (!window.__fragmentHandler) {
        window.__fragmentHandler = {
            updating: new Set()
        };
    }
    
    /**
     * Decode a base64-encoded search value from the URL fragment.
     * @param {string} fragment - The URL fragment (without #)
     * @returns {string} Decoded search query or empty string
     */
    window.__fragmentHandler.decodeFragment = function(fragment) {
        const params = new URLSearchParams(fragment);
        const searchValue = params.get('search') || '';
        
        if (!searchValue) {
            return '';
        }
        
        try {
            const padding = 4 - (searchValue.length % 4);
            const padded = padding !== 4 ? searchValue + '='.repeat(padding) : searchValue;
            return atob(padded);
        } catch (e) {
            return '';
        }
    };
    
    /**
     * Encode a search query to base64 and format as fragment.
     * @param {string} query - The search query to encode
     * @returns {string} Formatted fragment (e.g., "search=base64encoded")
     */
    window.__fragmentHandler.encodeFragment = function(query) {
        const queryText = (query || '').trim();
        
        if (!queryText) {
            return '';
        }
        
        try {
            const encoded = btoa(queryText).replace(/=+$/, '');
            const params = new URLSearchParams();
            params.set('search', encoded);
            return params.toString();
        } catch (e) {
            return '';
        }
    };
    
    /**
     * Read the current search query from the URL fragment.
     * @returns {string} Decoded search query or empty string
     */
    window.__fragmentHandler.readFragment = function() {
        const hash = window.location.hash;
        const fragment = hash.startsWith('#') ? hash.substring(1) : hash;
        return this.decodeFragment(fragment);
    };
    
    /**
     * Update the URL fragment with a new search query.
     * @param {string} query - The search query to encode and set
     */
    window.__fragmentHandler.updateFragment = function(query) {
        const newQuery = this.encodeFragment(query);
        const newHash = newQuery ? '#' + newQuery : '';
        
        // Mark as internal update
        this.updating.add(newHash);
        
        // Update fragment without creating history entry
        window.history.replaceState(null, '', newHash);
    };
    
    /**
     * Check if a hash change is an internal update we should ignore.
     * @param {string} hash - The hash to check
     * @returns {boolean} True if this is an internal update
     */
    window.__fragmentHandler.isInternalUpdate = function(hash) {
        if (this.updating.has(hash)) {
            this.updating.delete(hash);
            return true;
        }
        return false;
    };
})();

