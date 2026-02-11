/* imagededup-ui — Alpine.js application component */

function dedupApp() {
    return {
        groups: [],
        // Use an object for reactivity (Alpine doesn't track Set mutations)
        _discardedMap: {},
        currentIndex: 0,
        totalGroups: 0,
        loading: true,

        async init() {
            const [groupsRes, discardRes] = await Promise.all([
                fetch('/api/groups').then(r => r.json()),
                fetch('/api/discard').then(r => r.json()),
            ]);
            this.groups = groupsRes.groups;
            this.totalGroups = groupsRes.total_groups;

            // Build reactive object from array
            const map = {};
            for (const p of discardRes.discarded) {
                map[p] = true;
            }
            this._discardedMap = map;

            this.loading = false;

            // Keyboard navigation
            document.addEventListener('keydown', (e) => {
                if (e.key === 'ArrowLeft') this.prev();
                if (e.key === 'ArrowRight') this.next();
            });
        },

        get currentGroup() {
            if (this.groups.length === 0) {
                return { id: -1, images: [] };
            }
            return this.groups[this.currentIndex];
        },

        get progress() {
            return (this.currentIndex + 1) + ' / ' + this.totalGroups;
        },

        isDiscarded(path) {
            return !!this._discardedMap[path];
        },

        async toggleDiscard(path) {
            const discard = !this.isDiscarded(path);
            const res = await fetch('/api/discard', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path, discard }),
            });
            const data = await res.json();

            // Rebuild reactive map from server response
            const map = {};
            for (const p of data.discarded) {
                map[p] = true;
            }
            this._discardedMap = map;
        },

        prev() {
            if (this.currentIndex > 0) this.currentIndex--;
        },

        next() {
            if (this.currentIndex < this.totalGroups - 1) this.currentIndex++;
        },

        formatSize(bytes) {
            if (bytes < 1024) return bytes + ' B';
            if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
            return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
        },
    };
}
