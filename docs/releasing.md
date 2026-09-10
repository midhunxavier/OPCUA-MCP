# Releasing

Publishing is automated and tag-triggered. It is deliberately not a command you
run by hand — the npm package needs `npm run build` to stage `build/contract.json`
and `build/version.json`, and a hand-run `npm publish` that skips it ships a
package that dies at startup.

## One-time setup

Neither registry is configured yet; both are needed before the first release.

1. **npm** — create an automation token and add it as the `NPM_TOKEN` repository
   secret. Publishing uses `--provenance`, which needs `id-token: write` (already
   set in the workflow).
2. **PyPI** — add a
   [trusted publisher](https://docs.pypi.org/trusted-publishers/) for this repo,
   workflow `publish.yml`, environment `pypi`. No token to store.
3. Create the `pypi` GitHub environment (optionally with a required reviewer, so
   a publish needs an explicit approval).

## A note on READMEs

Each package's README ships *inside* its artifact — `files: [..., "README.md"]`
for npm, `readme = "README.md"` for the wheel — and registry pages are frozen per
version. So edits to `packages/server-node/README.md` or
`packages/server-python/README.md` appear on GitHub immediately but do not reach
npmjs.com or pypi.org until the next publish. Worth checking those two files
before cutting a release.

## Cutting a release

```bash
# 1. Bump all three manifests together — they release as a unit and a test
#    enforces that they match.
#    packages/server-node/package.json
#    packages/server-python/pyproject.toml
#    packages/mock-server/pyproject.toml

# 2. Move CHANGELOG entries from [Unreleased] into the new version, and add the
#    comparison link at the bottom.

# 3. Verify locally exactly as CI will.
cd packages/server-node && npm ci && npm run build && npm test && cd ../..
uv sync --all-packages
uv run ruff check . && uv run ruff format --check .
cd tests && uv run --no-sync pytest && uv run --no-sync pytest -m smoke smoke/

# 4. Commit, then tag. The tag must match the manifests; the workflow checks.
git tag v0.2.0 && git push origin v0.2.0
```

The `publish.yml` workflow then runs the full suite plus the artifact smoke
tests, and only publishes if they pass.

## After the first `opcua-mcp-server` release

The old npm name needs a pointer to the new one:

```bash
npm deprecate opcua-mcp-npx-server \
  "Renamed to opcua-mcp-server — https://github.com/midhunxavier/OPCUA-MCP"
```

**Do not unpublish it.** That breaks existing installs, and npm blocks unpublish
after 72 hours anyway.

## Why the smoke tests gate the release

They build the real tarball and wheel, install them somewhere isolated, and drive
the installed entry points. Everything else in CI runs from the source tree and
from `uv.lock`, so it cannot see packaging faults or a dependency range that
resolves to a breaking major. Both have already shipped broken releases here.
