import '@testing-library/jest-dom'
import { afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'

// Cleanup after each test
afterEach(() => {
    cleanup()
})

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
    root = null
    rootMargin = ''
    thresholds = []

    constructor() { }
    disconnect() { }
    observe() { }
    unobserve() { }
    takeRecords() { return [] }
}

// Mock ResizeObserver
global.ResizeObserver = class ResizeObserver {
    constructor() { }
    disconnect() { }
    observe() { }
    unobserve() { }
}

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: (query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: () => { },
        removeListener: () => { },
        addEventListener: () => { },
        removeEventListener: () => { },
        dispatchEvent: () => { },
    }),
})

// Mock window.scrollTo
Object.defineProperty(window, 'scrollTo', {
    writable: true,
    value: () => { },
})