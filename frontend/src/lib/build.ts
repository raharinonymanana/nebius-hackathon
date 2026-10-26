// Formats the frozen build identity (see demo/build_info.py) for the footer
// stamp. Pure: no DOM, no I/O -- unit-tested in build.test.ts.

export interface BuildInfo {
  name: string
  version: string
  commit: string
  built_utc: string | null
}

export interface BuildLabel {
  label: string // "build v1.0.0", "build 3bbde87", "build 3bbde87-dirty", "build dev"
  shortSha: string // 7-char commit sha, "" when unknown
  href: string // GitHub commit URL, "" when there is nothing to link to
}

const COMMIT_URL = 'https://github.com/raharinonymanana/nebius-hackathon/commit/'

// `git describe --tags --always --dirty` gives "v1.0.0", "v1.0.0-2-g3bbde87",
// "3bbde87" (no tag yet) or any of those with a "-dirty" suffix. We show the
// whole string verbatim after "build " so a tag, the commit distance and the
// dirty flag all stay visible; null (dev, no baked identity) -> "build dev".
export function formatBuild(info: BuildInfo | null): BuildLabel {
  if (!info) {
    return { label: 'build dev', shortSha: '', href: '' }
  }
  const shortSha = info.commit ? info.commit.slice(0, 7) : ''
  const href = info.commit ? `${COMMIT_URL}${info.commit}` : ''
  return { label: `build ${info.version}`, shortSha, href }
}
