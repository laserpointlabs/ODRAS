# Cursor Git Workflow Guidelines

**Document Version**: 1.0  
**Created**: October 10, 2025  
**Purpose**: Prevent git workflow mistakes during squash-merge operations

## 🚨 CRITICAL: Read Before Any Merge Operation

This document outlines the correct procedures for handling branches, merges, and squash-merges in ODRAS to prevent the mistakes that have occurred in the past.

## 🛡️ Core Principles

1. **Feature branches merge to main only**
2. **Never merge main into feature branches without permission**
3. **Always verify current branch before operations**
4. **Document and confirm before executing**
5. **Use GitHub PR process when possible**

## 📋 Pre-Merge Checklist

Before ANY merge operation:

```bash
# 1. Verify current branch
git branch --show-current

# 2. Check branch status
git status

# 3. Review recent commits
git log --oneline -5

# 4. Verify target branch
git log --oneline origin/main -5
```

## 🔄 Squash-Merge Workflow (Feature → Main)

### Step 1: Create Pull Request

```bash
# Preferred method using GitHub CLI
gh pr create --base main --head feature/branch-name --title "Description" --body "Details"

# Wait for CI to pass
gh pr checks

# Merge with squash
gh pr merge --squash --delete-branch
```

### Step 2: Alternative Direct Merge (Use Sparingly)

```bash
# Ensure you're on main
git checkout main
git pull origin main

# Squash merge the feature branch
git merge --squash feature/branch-name

# Create a clean commit
git commit -m "feat: Clear description of changes"

# Push to remote
git push origin main
```

### Step 3: Clean Up

```bash
# Delete local branch
git branch -D feature/branch-name

# Delete remote branch
git push origin --delete feature/branch-name

# Verify cleanup
git branch -a | grep feature/branch-name
```

## ❌ Common Mistakes to Avoid

### 1. Merging to Wrong Branch
```bash
# WRONG - Don't merge feature branches into each other
git checkout feature/ontology-work
git merge feature/connection-fixes  # NO!

# CORRECT - Each feature merges to main independently
git checkout main
git merge --squash feature/connection-fixes
```

### 2. Merging Main Into Feature Without Permission
```bash
# WRONG - Don't automatically update feature branches
git checkout feature/my-work
git merge main  # ASK FIRST!

# CORRECT - Ask user first
"Should I merge the latest main changes into your feature branch?"
```

### 3. Force Pushing Without Warning
```bash
# WRONG
git push --force origin feature/branch

# CORRECT
"This requires a force push. Are you sure? (explains consequences)"
git push --force-with-lease origin feature/branch
```

## 🎯 Decision Tree for Branch Operations

```
Is this a merge operation?
├─ YES → What type?
│   ├─ Feature → Main
│   │   └─ ✅ Proceed with squash-merge workflow
│   ├─ Main → Feature  
│   │   └─ ⚠️  ASK USER FIRST
│   └─ Feature → Feature
│       └─ ❌ NEVER DO THIS
└─ NO → Continue with operation
```

## 📝 Communication Template

Before complex operations, always state:

```
Current State:
- You are on branch: [branch name]
- This branch is [X commits ahead/behind] main
- Last commit: [commit message]

Proposed Action:
- I will [squash-merge/merge/rebase] [source] into [target]
- This will [expected outcome]
- CI status: [passing/failing/pending]

Potential Impact:
- [List any risks or side effects]

Do you want me to proceed? (yes/no)
```

## 🔍 Post-Merge Verification

After any merge:

```bash
# 1. Verify the merge
git log --oneline --graph -10

# 2. Check file changes
git diff HEAD~1

# 3. Verify remote state
git fetch --all
git branch -vv

# 4. Run tests locally if requested
./odras.sh test
```

## 🚨 Emergency Recovery

If something goes wrong:

### Undo Last Commit (not pushed)
```bash
git reset --hard HEAD~1
```

### Undo Pushed Merge
```bash
# Create revert commit
git revert -m 1 HEAD
git push origin main
```

### Reset Feature Branch
```bash
git checkout feature/branch
git reset --hard origin/feature/branch
```

## 📋 Quick Reference

| Operation | Command | When to Use |
|-----------|---------|-------------|
| Squash merge to main | `gh pr merge --squash` | Feature complete |
| Update feature from main | `git merge main` | ASK FIRST |
| Delete merged branch | `git branch -D branch` | After squash-merge |
| Check branch status | `git branch -vv` | Before operations |
| View recent changes | `git log --oneline -10` | Always |

## 🎓 Learning from Past Mistakes

### Incident: Connection Pool Fix Merge (Oct 10, 2025)
- **Mistake**: Merged connection pool fixes into feature branch without asking
- **Impact**: Mixed unrelated changes in feature branch
- **Lesson**: Always keep feature branches focused on their specific work
- **Prevention**: Ask before merging main into any feature branch

## 🏆 Golden Rules

1. **When in doubt, ask**
2. **Feature branches are sacred - don't pollute them**
3. **Main is the single source of truth**
4. **Squash-merge keeps history clean**
5. **Always clean up after merging**
6. **Document what you're doing before you do it**

---

**Remember**: This document exists because mistakes were made. Follow it religiously to maintain a clean, professional git workflow.
