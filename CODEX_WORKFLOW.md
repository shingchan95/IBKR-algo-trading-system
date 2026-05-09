# CODEX_WORKFLOW.md

## Recommended workflow

This project can use Codex to speed up development, but because it is a trading system, use Git and branches carefully.

## One-time setup

From the project root:

```bash
cd ~/Documents/trading-system
git status
```

Make sure `main` is clean.

Create a Codex branch:

```bash
git checkout -b codex/backtest-runner
```

Start Codex from the project root:

```bash
codex --full-auto
```

## First prompt to Codex

Paste this into Codex:

```text
Read AGENTS.md and CODEX_TASKS.md. Work on Task 1 only. Do not run paper or live trading. Do not connect to IBKR. After Task 1, run only the allowed syntax check, show changed files, summarise the change, and stop.
```

## After Codex finishes a task

In a normal terminal, run:

```bash
git status
git diff
```

If the changes look good:

```bash
git add .
git commit -m "Add generic Nautilus backtest runner"
```

Then go back to Codex and say:

```text
Now do Task 2 only. Follow AGENTS.md. Stop after Task 2.
```

Repeat this pattern:

1. Codex does one task.
2. You check `git diff`.
3. You commit.
4. You ask for the next task.

## If Codex makes a mess

Undo one file:

```bash
git checkout -- path/to/file.py
```

Undo all uncommitted changes:

```bash
git reset --hard
```

Return to main if needed:

```bash
git checkout main
```

Delete the Codex branch if needed:

```bash
git branch -D codex/backtest-runner
```

## Full-auto caution

Full-auto can edit files and run commands with less interruption.

Use it only on a separate branch.

Do not use it on `main`.

Do not let it run live or paper trading.

Do not let it run anything with:

```bash
ENABLE_ORDER_PLACEMENT=true
```

## Useful commands

Check branch:

```bash
git branch
```

Check changes:

```bash
git status
git diff
```

Syntax check:

```bash
python -m compileall backtests infra strategies scripts
```

Push branch to GitHub:

```bash
git push -u origin codex/backtest-runner
```
