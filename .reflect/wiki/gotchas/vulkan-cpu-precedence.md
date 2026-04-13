---
created: 2026-04-13
updated: 2026-04-13
sources: [checkpoint 9c595bc9b42d]
tags: [node-llama-cpp, vulkan, cpu, prebuilt-binaries]
status: active
---

# node-llama-cpp Prefers Vulkan Over CPU

## The Gotcha

When both Vulkan and CPU-only prebuilt binaries are available, `node-llama-cpp` will auto-select the Vulkan prebuilt, even if your use case requires only CPU inference. This creates a hard dependency on the Vulkan SDK at build time. If the SDK is absent, the build will fail with source compilation errors instead of gracefully falling back to CPU mode. (checkpoint 9c595bc9b42d)

## When It Occurs

This auto-selection happens during `node-llama-cpp` initialization when:
- Both GPU (Vulkan) and CPU-only prebuilt packages are installed
- The Vulkan SDK is not present on the system
- The build process attempts to compile from source as a fallback

## Impact

The symptom is a confusing compile failure that does not clearly indicate the root cause: the module tries to use Vulkan, finds the SDK missing, and fails instead of reverting to CPU mode. This can mask the real issue — that you don't need GPU acceleration but the toolchain is forcing it.

## Solution

To force CPU-only inference, explicitly remove the Vulkan prebuilt package from your environment or dependencies. This removes the preference conflict and allows `node-llama-cpp` to use the CPU-only prebuilt binary.

## Context

This behavior was encountered during `reflect init` testing with qmd's llama.cpp integration, where CPU-only inference was sufficient and the Vulkan SDK was not available. The fix involved identifying and removing the unwanted Vulkan package, after which the CPU-only build proceeded successfully.
