/**
 * Fuzzy string matching utilities for typo-tolerant search.
 */

/** Damerau-Levenshtein distance (handles transpositions like "Karnakata" → "Karnataka") */
export function editDistance(a: string, b: string): number {
  a = a.toLowerCase()
  b = b.toLowerCase()
  if (a === b) return 0
  if (a.length === 0) return b.length
  if (b.length === 0) return a.length

  const dp: number[][] = Array.from({ length: a.length + 1 }, (_, i) =>
    Array.from({ length: b.length + 1 }, (_, j) => (i === 0 ? j : j === 0 ? i : 0))
  )

  for (let i = 1; i <= a.length; i++) {
    for (let j = 1; j <= b.length; j++) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1
      dp[i][j] = Math.min(
        dp[i - 1][j] + 1,       // deletion
        dp[i][j - 1] + 1,       // insertion
        dp[i - 1][j - 1] + cost // substitution
      )
      // transposition
      if (i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) {
        dp[i][j] = Math.min(dp[i][j], dp[i - 2][j - 2] + cost)
      }
    }
  }
  return dp[a.length][b.length]
}

/** Max allowed edit distance based on query length */
function maxDist(len: number): number {
  if (len <= 3) return 0
  if (len <= 6) return 1
  return 2
}

/**
 * Returns true if query fuzzy-matches target.
 * Handles substrings, transpositions, and off-by-one typos.
 */
export function fuzzyMatch(query: string, target: string): boolean {
  const q = query.toLowerCase().trim()
  const t = target.toLowerCase()
  if (!q) return true
  // Exact substring
  if (t.includes(q)) return true
  // Each word in query fuzzy-matches some part of target
  const words = q.split(/\s+/)
  const targetWords = t.split(/[\s,]+/)
  return words.every(w =>
    targetWords.some(tw => editDistance(w, tw) <= maxDist(w.length)) ||
    t.includes(w)
  )
}
