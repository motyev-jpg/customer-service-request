# Practice: how we build csrm-dashboard

This file defines the working process. `concept.md` defines what we build.

## Workflow

1. **Planning phase.** The user may ask for a plan, design, or analysis. Claude answers with a plan only. No files are created or changed, and no commits are made.
2. **Build trigger.** Claude starts building only when the user writes **"please build"**. Any other message, including a request for a plan, is not a trigger.
3. **Merge trigger.** Claude merges `dev` into `main` only when the user writes **"please merge"**.
4. If a request is unclear, Claude asks before building.

## Git and GitHub

- The project is saved to GitHub. Remote: `origin`.
- Repository name: `customer-service-request`. Visibility: **public**.
- Because the repo is public, never commit secrets, customer data, or real service request content. Use sample or anonymized data only.
- Two long-lived branches: `main` (stable, released) and `dev` (work in progress).
- All build work is committed to `dev`. Claude never commits directly to `main`.
- After each "please build", Claude commits to `dev` and pushes `dev` to GitHub.
- On "please merge":
  1. Update `README.md` so it reflects the current state of the dashboard.
  2. Commit the README update to `dev`.
  3. Merge `dev` into `main` and push `main`.
  4. Switch back to `dev`.
- No force-push, no history rewriting, no deleting branches without explicit approval.
- Commit messages: short imperative summary line (for example, `Add ticket status filter`), details in the body when needed.
- Never commit secrets (tokens, passwords, `.env`). Keep them in `.env`, listed in `.gitignore`, and provide `.env.example` with placeholder values.

## README.md

- Describes the dashboard: purpose, main features, screenshots if relevant, setup, run instructions, configuration, and project structure.
- Updated on every merge to `main`, as part of the merge flow above.
- Must match what is actually in `main` at that moment.

## Rules for Claude

- Read `practice.md` and `concept.md` before starting any work.
- Reply in Hebrew. Code, comments, commit messages, and README are in English.
- Keep answers short.
- After each build, report briefly: what changed, which commit, and anything that was not done or failed.
