/**
 * Design Tokens Enforcement Test
 *
 * This test ensures that all components use semantic design tokens
 * instead of hardcoded Tailwind color classes.
 *
 * ALLOWED: bg-primary, text-status-success, border-state-ai, etc.
 * FORBIDDEN: bg-green-100, text-red-500, border-yellow-200, etc.
 */

import { describe, it, expect } from 'vitest'
import * as fs from 'fs'
import * as path from 'path'

// Directories to scan for design token violations
const SCAN_DIRECTORIES = ['app', 'components', 'lib']

// Files/directories to ignore
const IGNORE_PATTERNS = [
  'node_modules',
  '.next',
  '__tests__',
  'globals.css',
  'tailwind.config',
  // Market Intelligence uses data visualization colors that don't have semantic equivalents
  'market-intelligence',
]

// Hardcoded color patterns that should NOT be used
// These are raw Tailwind color utilities that bypass our design tokens
const FORBIDDEN_PATTERNS = [
  // Background colors
  /\bbg-(red|green|blue|yellow|orange|purple|pink|indigo|teal|cyan|emerald|amber|lime|rose|fuchsia|violet|sky|slate|zinc|neutral|stone)-\d{2,3}\b/g,
  // Text colors
  /\btext-(red|green|blue|yellow|orange|purple|pink|indigo|teal|cyan|emerald|amber|lime|rose|fuchsia|violet|sky|slate|zinc|neutral|stone)-\d{2,3}\b/g,
  // Border colors
  /\bborder-(red|green|blue|yellow|orange|purple|pink|indigo|teal|cyan|emerald|amber|lime|rose|fuchsia|violet|sky|slate|zinc|neutral|stone)-\d{2,3}\b/g,
  // Ring colors
  /\bring-(red|green|blue|yellow|orange|purple|pink|indigo|teal|cyan|emerald|amber|lime|rose|fuchsia|violet|sky|slate|zinc|neutral|stone)-\d{2,3}\b/g,
  // Divide colors
  /\bdivide-(red|green|blue|yellow|orange|purple|pink|indigo|teal|cyan|emerald|amber|lime|rose|fuchsia|violet|sky|slate|zinc|neutral|stone)-\d{2,3}\b/g,
  // Outline colors
  /\boutline-(red|green|blue|yellow|orange|purple|pink|indigo|teal|cyan|emerald|amber|lime|rose|fuchsia|violet|sky|slate|zinc|neutral|stone)-\d{2,3}\b/g,
  // Shadow colors
  /\bshadow-(red|green|blue|yellow|orange|purple|pink|indigo|teal|cyan|emerald|amber|lime|rose|fuchsia|violet|sky|slate|zinc|neutral|stone)-\d{2,3}\b/g,
  // Accent colors
  /\baccent-(red|green|blue|yellow|orange|purple|pink|indigo|teal|cyan|emerald|amber|lime|rose|fuchsia|violet|sky|slate|zinc|neutral|stone)-\d{2,3}\b/g,
  // Decoration colors
  /\bdecoration-(red|green|blue|yellow|orange|purple|pink|indigo|teal|cyan|emerald|amber|lime|rose|fuchsia|violet|sky|slate|zinc|neutral|stone)-\d{2,3}\b/g,
  // Fill colors
  /\bfill-(red|green|blue|yellow|orange|purple|pink|indigo|teal|cyan|emerald|amber|lime|rose|fuchsia|violet|sky|slate|zinc|neutral|stone)-\d{2,3}\b/g,
  // Stroke colors
  /\bstroke-(red|green|blue|yellow|orange|purple|pink|indigo|teal|cyan|emerald|amber|lime|rose|fuchsia|violet|sky|slate|zinc|neutral|stone)-\d{2,3}\b/g,
  // Caret colors
  /\bcaret-(red|green|blue|yellow|orange|purple|pink|indigo|teal|cyan|emerald|amber|lime|rose|fuchsia|violet|sky|slate|zinc|neutral|stone)-\d{2,3}\b/g,
  // Placeholder colors
  /\bplaceholder-(red|green|blue|yellow|orange|purple|pink|indigo|teal|cyan|emerald|amber|lime|rose|fuchsia|violet|sky|slate|zinc|neutral|stone)-\d{2,3}\b/g,
  // From/via/to gradient colors
  /\b(from|via|to)-(red|green|blue|yellow|orange|purple|pink|indigo|teal|cyan|emerald|amber|lime|rose|fuchsia|violet|sky|slate|zinc|neutral|stone)-\d{2,3}\b/g,
]

// Allowed exceptions - patterns that look like violations but are actually fine
const ALLOWED_EXCEPTIONS: RegExp[] = [
  // Gray scale is acceptable for neutral UI elements (muted text, borders, backgrounds)
  // These are semantic-neutral colors that work well for disabled states, dividers, etc.
  /\b(bg|text|border|ring|divide)-gray-\d{2,3}\b/g,
]

interface Violation {
  file: string
  line: number
  column: number
  match: string
  context: string
}

function shouldIgnoreFile(filePath: string): boolean {
  return IGNORE_PATTERNS.some((pattern) => filePath.includes(pattern))
}

function isAllowedException(match: string): boolean {
  return ALLOWED_EXCEPTIONS.some((pattern) => pattern.test(match))
}

function scanFile(filePath: string): Violation[] {
  const violations: Violation[] = []
  const content = fs.readFileSync(filePath, 'utf-8')
  const lines = content.split('\n')

  lines.forEach((line, lineIndex) => {
    FORBIDDEN_PATTERNS.forEach((pattern) => {
      // Reset regex lastIndex for global patterns
      pattern.lastIndex = 0
      let match: RegExpExecArray | null

      while ((match = pattern.exec(line)) !== null) {
        if (!isAllowedException(match[0])) {
          violations.push({
            file: filePath,
            line: lineIndex + 1,
            column: match.index + 1,
            match: match[0],
            context: line.trim().substring(0, 100),
          })
        }
      }
    })
  })

  return violations
}

function scanDirectory(dir: string): Violation[] {
  const violations: Violation[] = []
  const absoluteDir = path.join(process.cwd(), dir)

  if (!fs.existsSync(absoluteDir)) {
    return violations
  }

  function walkDir(currentDir: string) {
    const files = fs.readdirSync(currentDir)

    files.forEach((file) => {
      const filePath = path.join(currentDir, file)
      const stat = fs.statSync(filePath)

      if (shouldIgnoreFile(filePath)) {
        return
      }

      if (stat.isDirectory()) {
        walkDir(filePath)
      } else if (/\.(tsx|jsx|ts|js)$/.test(file)) {
        violations.push(...scanFile(filePath))
      }
    })
  }

  walkDir(absoluteDir)
  return violations
}

describe('Design Tokens Enforcement', () => {
  it('should not use hardcoded Tailwind color classes', () => {
    const allViolations: Violation[] = []

    SCAN_DIRECTORIES.forEach((dir) => {
      allViolations.push(...scanDirectory(dir))
    })

    if (allViolations.length > 0) {
      const errorMessage = [
        '\n❌ Design Token Violations Found!\n',
        'The following files use hardcoded Tailwind colors instead of semantic design tokens:\n',
        ...allViolations.map(
          (v) =>
            `  ${v.file}:${v.line}:${v.column}\n` +
            `    Found: "${v.match}"\n` +
            `    Context: ${v.context}\n`
        ),
        '\n📚 How to fix:',
        '  Replace hardcoded colors with semantic tokens:',
        '    bg-green-100  → bg-status-success',
        '    text-green-800 → text-status-success-foreground',
        '    bg-yellow-100 → bg-status-warning',
        '    text-yellow-800 → text-status-warning-foreground',
        '    bg-red-100    → bg-status-error',
        '    text-red-800  → text-status-error-foreground',
        '    bg-blue-100   → bg-status-info',
        '    text-blue-800 → text-status-info-foreground',
        '\n  For trust levels:',
        '    bg-green-*    → bg-trust-verde',
        '    bg-yellow-*   → bg-trust-amarelo',
        '    bg-orange-*   → bg-trust-laranja',
        '    bg-red-*      → bg-trust-vermelho',
        '\n  For state colors:',
        '    (handoff)     → bg-state-handoff, text-state-handoff-foreground',
        '    (AI/active)   → bg-state-ai, text-state-ai-foreground',
        '    (recording)   → bg-state-recording, text-state-recording-foreground',
        '\n  See globals.css and tailwind.config.js for all available tokens.',
        '\n',
      ].join('\n')

      expect(allViolations).toHaveLength(0)
      // This will show the detailed error message when test fails
      throw new Error(errorMessage)
    }

    expect(allViolations).toHaveLength(0)
  })

  it('should have design tokens defined in globals.css', () => {
    const globalsPath = path.join(process.cwd(), 'app/globals.css')
    const content = fs.readFileSync(globalsPath, 'utf-8')

    // Check for essential token categories
    const requiredTokens = [
      '--status-success',
      '--status-warning',
      '--status-error',
      '--status-info',
      '--status-neutral',
      '--state-handoff',
      '--state-ai',
      '--state-recording',
      '--trust-verde',
      '--trust-amarelo',
      '--trust-vermelho',
    ]

    requiredTokens.forEach((token) => {
      expect(content).toContain(token)
    })
  })

  it('should have design tokens mapped in tailwind.config.js', () => {
    const configPath = path.join(process.cwd(), 'tailwind.config.js')
    const content = fs.readFileSync(configPath, 'utf-8')

    // Check for essential token mappings
    const requiredMappings = ['status:', 'state:', 'trust:']

    requiredMappings.forEach((mapping) => {
      expect(content).toContain(mapping)
    })
  })
})
