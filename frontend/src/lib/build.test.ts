import { describe, it, expect } from 'vitest'
import { formatBuild } from './build'

const SHA = '4a1b2c3d5e6f70819a2b3c4d5e6f708192a3b4c5' // full 40-char commit
const HREF = `https://github.com/raharinonymanana/nebius-hackathon/commit/${SHA}`

describe('formatBuild', () => {
  it('exact tag -> "build <tag>", linked to the commit', () => {
    const b = formatBuild({ name: 'melodie', version: 'v1.0.0', commit: SHA, built_utc: null })
    expect(b.label).toBe('build v1.0.0')
    expect(b.shortSha).toBe('4a1b2c3')
    expect(b.href).toBe(HREF)
  })

  it('tag + N commits -> the whole describe string stays visible', () => {
    const b = formatBuild({
      name: 'melodie', version: 'v1.0.0-2-g3bbde87', commit: SHA, built_utc: null,
    })
    expect(b.label).toBe('build v1.0.0-2-g3bbde87')
    expect(b.href).toBe(HREF)
  })

  it('no tag yet -> "build <sha>"', () => {
    const b = formatBuild({ name: 'melodie', version: '3bbde87', commit: SHA, built_utc: null })
    expect(b.label).toBe('build 3bbde87')
    expect(b.shortSha).toBe('4a1b2c3')
  })

  it('dirty suffix stays visible', () => {
    const b = formatBuild({ name: 'melodie', version: '3bbde87-dirty', commit: SHA, built_utc: null })
    expect(b.label).toBe('build 3bbde87-dirty')
  })

  it('null -> "build dev", no link', () => {
    const b = formatBuild(null)
    expect(b.label).toBe('build dev')
    expect(b.shortSha).toBe('')
    expect(b.href).toBe('')
  })
})
