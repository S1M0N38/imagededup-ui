# Changelog

## 0.1.0 (2026-02-11)


### Features

* **analyzer:** add image analysis and duplicate grouping ([108dfb9](https://github.com/S1M0N38/imagededup-ui/commit/108dfb9b097c90b45791b8d3633937dda6166c96))
* **cache:** add cache management for .imagededup/ directory ([f3b32df](https://github.com/S1M0N38/imagededup-ui/commit/f3b32dfa89f04e0e98412c9ef888296666ba465d))
* **cli:** add CLI argument parsing and orchestration ([47c101f](https://github.com/S1M0N38/imagededup-ui/commit/47c101fb6d75fd1c86771e106aebc4cb7246e65d))
* **deps:** add imagededup and tqdm dependencies ([748f0a4](https://github.com/S1M0N38/imagededup-ui/commit/748f0a473d9a1e3edfd3e687ec9a8664b0a09afa))
* initialize project from template ([97d41d1](https://github.com/S1M0N38/imagededup-ui/commit/97d41d15d65cb1173e5611472f37786c6cb87ea4))
* **server:** add HTTP server with API routes and image serving ([a4c5cb1](https://github.com/S1M0N38/imagededup-ui/commit/a4c5cb1e13b9ceeaf3d5f34a3a6ef7d40f02f362))
* **ui:** add Alpine.js frontend with gallery-grade design ([384083f](https://github.com/S1M0N38/imagededup-ui/commit/384083f6e8e833f7ff55a8f0290ff36ccd54f07d))


### Bug Fixes

* **analyzer:** ensure normalize_score returns native Python float ([e4f86c3](https://github.com/S1M0N38/imagededup-ui/commit/e4f86c3d51050599352ed3846a2d71f5d5f3e59a))
* **cache:** cast numpy float32 scores to float for JSON serialization ([0c5495f](https://github.com/S1M0N38/imagededup-ui/commit/0c5495f7f36977d2d5109d7c885294a234c9d39c))
* **ui:** remove duplicate x-init causing arrow navigation to skip groups ([2b82938](https://github.com/S1M0N38/imagededup-ui/commit/2b82938abba13ab9476488d7a946912308ce5fb1))


### Documentation

* **docs:** add code conventions to CLAUDE.md ([784dd63](https://github.com/S1M0N38/imagededup-ui/commit/784dd63d61a98df97f3a8bf6a7d0f237d4bf5152))
* **docs:** clarify PRD with API spec, CLI flags, and UI behavior ([f848f16](https://github.com/S1M0N38/imagededup-ui/commit/f848f1678a9cf713bed4fc002b80fa4ae6536e5f))
* **readme:** add readme for imagededup-ui ([37fc349](https://github.com/S1M0N38/imagededup-ui/commit/37fc349330c0be94c28b3e985d5627f0d83daf19))
* **readme:** remove image caption ([b0063c2](https://github.com/S1M0N38/imagededup-ui/commit/b0063c2e7a22025468652f052317f0453b7c6286))
