# Security Policy

## Reporting a vulnerability

Please report security issues **privately** — do not open a public issue for
anything security-sensitive.

- Preferred: enable and use GitHub's [private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability)
  for this repository (Security tab → "Report a vulnerability").
- Or email the maintainer at the address listed on the repository owner's profile.

Please include steps to reproduce and the affected version/commit. We aim to
acknowledge reports within a few business days.

## Supported versions

This project is distributed as source. Security fixes are applied to the
`master` branch; users should track the latest commit.

## Handling secrets

This server requires a `USPTO_API_KEY` (and optionally `PATENTSVIEW_API_KEY`).

- **Never commit API keys, tokens, or `.env` files.** Supply credentials only
  via environment variables or Docker MCP secrets.
- The `catalog.yaml` gateway definition references secrets by name
  (`{{uspto.api_key}}`) — never inline a literal key value into it.
- `.gitignore` excludes `.env`, `*.bak`, `__pycache__/`, and local tooling
  directories to reduce the risk of accidental credential exposure.
- If a credential is ever committed, **rotate it immediately** — rotation, not
  history rewriting, is what actually neutralizes an exposed secret.
