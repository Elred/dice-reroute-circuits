/**
 * Tests for project-versioning spec
 * Tasks 5.1, 5.2, 5.3, 5.4
 */
import { describe, it, expect } from 'vitest'
import * as fc from 'fast-check'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const SEMVER_REGEX = /^\d+\.\d+\.\d+$/

// Inline script logic: replaces or inserts the Version: line in about.md content
function applyVersionToAboutContent(content: string, version: string): string {
  if (/^Version: .+$/m.test(content)) {
    return content.replace(/^Version: .+$/m, `Version: ${version}`)
  } else {
    return content.replace(/^## Version$/m, `## Version\n\nVersion: ${version}`)
  }
}

// ---------------------------------------------------------------------------
// 5.1 — Property 1: SemVer format validation
// Validates: Requirements 1.2
// ---------------------------------------------------------------------------
describe('Property 1: SemVer format validation', () => {
  it('accepts any valid SemVer triple (non-negative integers)', () => {
    fc.assert(
      fc.property(
        fc.nat(), fc.nat(), fc.nat(),
        (major, minor, patch) => {
          const version = `${major}.${minor}.${patch}`
          expect(SEMVER_REGEX.test(version)).toBe(true)
        }
      ),
      { numRuns: 200 }
    )
  })

  it('rejects strings that are not valid SemVer', () => {
    // Arbitrary strings that are NOT of the form \d+.\d+.\d+
    const nonSemVer = fc.oneof(
      // strings with letters
      fc.stringMatching(/[a-zA-Z]/),
      // only one or two numeric segments
      fc.nat().map(n => `${n}`),
      fc.tuple(fc.nat(), fc.nat()).map(([a, b]) => `${a}.${b}`),
      // four segments
      fc.tuple(fc.nat(), fc.nat(), fc.nat(), fc.nat()).map(([a, b, c, d]) => `${a}.${b}.${c}.${d}`),
      // negative numbers (with minus sign)
      fc.integer({ min: -1000, max: -1 }).map(n => `${n}.0.0`),
    )

    fc.assert(
      fc.property(nonSemVer, (s) => {
        expect(SEMVER_REGEX.test(s)).toBe(false)
      }),
      { numRuns: 200 }
    )
  })
})

// ---------------------------------------------------------------------------
// 5.2 — Property 2: about.md round-trip
// Validates: Requirements 2.1, 2.3, 3.1
// ---------------------------------------------------------------------------
describe('Property 2: about.md round-trip', () => {
  it('for any valid SemVer, the script logic writes that exact version into about.md content', () => {
    // Use a realistic about.md template (with an existing Version: line)
    const baseContent = `## Version\n\nVersion: 0.0.0\n\nSome other content.\n`

    fc.assert(
      fc.property(
        fc.nat(), fc.nat(), fc.nat(),
        (major, minor, patch) => {
          const version = `${major}.${minor}.${patch}`
          const result = applyVersionToAboutContent(baseContent, version)
          expect(result).toContain(`Version: ${version}`)
        }
      ),
      { numRuns: 200 }
    )
  })
})

// ---------------------------------------------------------------------------
// 5.3 — Property 3: about.md uniqueness
// Validates: Requirements 3.2
// ---------------------------------------------------------------------------
describe('Property 3: about.md uniqueness', () => {
  it('after script logic runs, about.md has exactly one Version: line matching the input version', () => {
    const baseContent = `## Version\n\nVersion: 0.0.0\n\nSome other content.\n`

    fc.assert(
      fc.property(
        fc.nat(), fc.nat(), fc.nat(),
        (major, minor, patch) => {
          const version = `${major}.${minor}.${patch}`
          const result = applyVersionToAboutContent(baseContent, version)
          const versionLines = result.split('\n').filter(line => /^Version: .+$/.test(line))
          expect(versionLines).toHaveLength(1)
          expect(versionLines[0]).toBe(`Version: ${version}`)
        }
      ),
      { numRuns: 200 }
    )
  })
})

// ---------------------------------------------------------------------------
// 5.4 — Example test: __APP_VERSION__ equals package.json#version
// ---------------------------------------------------------------------------
describe('Example: __APP_VERSION__ equals package.json version', () => {
  it('__APP_VERSION__ matches the version field in package.json', () => {
    const pkgPath = resolve(__dirname, '../../package.json')
    const pkg = JSON.parse(readFileSync(pkgPath, 'utf-8'))
    const expectedVersion: string = pkg.version

    // __APP_VERSION__ is injected by Vite's define at compile time
    expect(__APP_VERSION__).toBe(expectedVersion)
  })
})
