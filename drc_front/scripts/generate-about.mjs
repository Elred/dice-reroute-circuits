// scripts/generate-about.mjs
import { readFileSync, writeFileSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const root = resolve(__dirname, '..')

// Read version from package.json
let version
try {
  const pkg = JSON.parse(readFileSync(resolve(root, 'package.json'), 'utf-8'))
  version = pkg.version
  if (!version) throw new Error('version field is missing')
} catch (err) {
  console.error(`generate-about: failed to read package.json: ${err.message}`)
  process.exit(1)
}

// Read or create about.md
const aboutPath = resolve(root, 'public/doc/about.md')
let content
try {
  content = readFileSync(aboutPath, 'utf-8')
} catch {
  content = `## Version\n\nVersion: ${version}\n`
  writeFileSync(aboutPath, content, 'utf-8')
  console.log(`generate-about: created about.md with Version: ${version}`)
  process.exit(0)
}

// Replace or insert version line
if (/^Version: .+$/m.test(content)) {
  content = content.replace(/^Version: .+$/m, `Version: ${version}`)
} else {
  content = content.replace(/^## Version$/m, `## Version\n\nVersion: ${version}`)
}

writeFileSync(aboutPath, content, 'utf-8')
console.log(`generate-about: set Version: ${version} in about.md`)
