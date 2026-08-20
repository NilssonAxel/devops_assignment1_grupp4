# Contributing
 
How we work in this repo. Read this before your first pull request. It's short on purpose — keep it that way.
 
## Local setup
 
- Python 3.13
- Install the dev tools:
```bash
  pip install ruff pytest
  pip install -r requirements.txt   # if present
```
- Run the same checks CI runs, before you push:
```bash
  ruff check .          # lint
  ruff format --check . # formatting
  pytest                # once the repo has tests
```
  Ruff covers linting *and* formatting (it replaces flake8, black, and isort). If `ruff format --check` fails, run `ruff format .` to fix it.
 
## Branching
 
We use **GitHub flow**: branch off `main`, open a PR, merge back. `main` is always deployable.
 
Name branches `type/short-description` — lowercase, kebab-case, imperative:
 
```
docs/contributing
feature/add-logging
fix/null-timestamps
chore/update-deps
```
 
Types: `feature`, `fix`, `chore` (tooling/config, no product code), `docs`, `refactor`, `test`. Pick the obvious one — it's a signpost, not a law. Name the *purpose*, not the file list (`docs/contributing`, not `docs/add-contributing-and-readme`).
 
## Making a change
 
1. Branch off the latest `main`.
2. Commit in the imperative present: "Add ruff CI", not "Added ruff CI".
3. Push and open a pull request into `main`.
4. Get two approving reviews. CI must be green.
5. **Squash and merge** — keeps `main`'s history to one clean commit per PR.
6. Delete the branch after merging.
Don't push directly to `main` — it's blocked anyway (see below).
 
## `main` protection
 
These rules are enforced on `main`, so you can't bypass them by accident:
 
- No direct pushes — changes come through a PR.
- **Two approving reviews** before merge — with 5 of us, author + 2 reviewers means a majority has signed off on every change. Anyone can approve.
- The **`ci`** status check must pass before merge.
## Secrets and files we never commit
 
Never commit credentials — once a secret is in git history it's compromised, even after you delete it. The Python `.gitignore` template already covers the common one:
 
```
.env
```
 
If the group later picks up tools with their own credential files (Terraform, Databricks, cloud keys, and so on), add the matching ignore patterns then — one decision per tool, once we've agreed to use it.
 
Dependabot alerts are on. If you hit a blocked push complaining about a secret, don't work around it — rotate the credential and keep it out of the repo.
