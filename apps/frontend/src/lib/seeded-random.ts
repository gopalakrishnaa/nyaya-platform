/**
 * Mulberry32 — deterministic PRNG seeded per-case.
 * Matches mock_api.py's per-case determinism.
 */
export function createRng(seed: number) {
  let s = seed >>> 0
  function next(): number {
    s += 0x6d2b79f5
    let t = s
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 0x100000000
  }
  return {
    random: next,
    randint(lo: number, hi: number) {
      return lo + Math.floor(next() * (hi - lo + 1))
    },
    choice<T>(arr: readonly T[]): T {
      return arr[Math.floor(next() * arr.length)]
    },
    sample<T>(arr: readonly T[], k: number): T[] {
      const copy = [...arr]
      const result: T[] = []
      for (let i = 0; i < k && copy.length; i++) {
        const idx = Math.floor(next() * copy.length)
        result.push(copy.splice(idx, 1)[0])
      }
      return result
    },
  }
}
