# Contributing - RestaurantRush (SC2002)

## 1. Setup
```bash
git clone <repo-url> && cd RestaurantRush
git config pull.rebase true
```

## 2. Branch Management
Every issue committed on a single branch.

```bash
# Creation of new Branch
git branch <branch-name>
git switch <branch-name>

# Rebasing
git pull --rebase origin main
git switch main
```

### Branch Name Convention
> `<type>/s<stage>-<slug>`
> e.g. feat/s1-waiter-seat

Types include:
* feature - New feature
* fix - Fix
* chore - Documentation
* refactor - Restructuring with no behaviour change

### Stage Tagging and Release
```bash
git tag -a stage-<stage_number> -m "Release Stage <stage_number>"
```

## 3. Commit Management
```bash
git add .
git commit - m "<commit_msg>"
git push
```

### Commit Name Convention
> `<type>(<scope>): <subject>
> e.g. fix(controller): stop charging customers during READY_TO_PAY

