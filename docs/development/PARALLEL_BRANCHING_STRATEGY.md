# Parallel Branching Strategy for MVP Development

## Overview

This strategy enables multiple Cursor agents to work simultaneously on different components while maintaining clean git workflow and minimizing conflicts.

**Last Updated:** October 31, 2025  
**Strategy:** Parallel feature branches with coordination

## Branch Structure

### Independent Feature Branches (Can Run in Parallel)

These branches can be worked on simultaneously by different agents with minimal conflict risk:

1. **`feature/workbench-fixes`** (Grouped fixes)
   - Issues: #63, #64, #66, #49
   - Scope: Individual tables count, renaming issues, ontology improvements
   - Risk: Low-medium (touches same files but different features)
   - **Recommendation:** Single agent, grouped together

2. **`feature/cqmt-das-workflow`** 
   - Issue: #65
   - Scope: DAS-driven CQMT workflow
   - Risk: Low (CQMT tab specific)
   - **Recommendation:** Can run parallel with workbench-fixes

3. **`feature/conceptualizer-fuseki`**
   - Issue: #61
   - Scope: Store individuals in Fuseki for CQ compatibility
   - Risk: Low (conceptualizer service specific)
   - **Recommendation:** Can run parallel

4. **`feature/thread-restore`**
   - Epic: #70
   - Scope: Thread persistence and restore
   - Risk: Low (DAS/thread management specific)
   - **Recommendation:** Can run parallel (independent epic)

5. **`feature/configurator-workbench`**
   - New workbench (plugin pattern)
   - Scope: Build configurator as plugin
   - Risk: Very Low (new code, no existing conflicts)
   - **Recommendation:** Perfect for parallel work

6. **`feature/tabularizer-workbench`**
   - New workbench (plugin pattern)
   - Scope: Build tabularizer as plugin
   - Risk: Very Low (new code, no existing conflicts)
   - **Recommendation:** Perfect for parallel work

7. **`feature/data-manager-workbench`**
   - Issue: #54
   - Scope: Build data manager as plugin
   - Risk: Very Low (new code, no existing conflicts)
   - **Recommendation:** Perfect for parallel work

8. **`feature/das-training-system`**
   - Epic: #67 (4 phases)
   - Scope: Chat history integration for DAS training
   - Risk: Low (new service, new endpoints)
   - **Recommendation:** Can run parallel

## Coordination Strategy

### High Independence (Safe for Parallel)
- Configurator, Tabularizer, Data Manager (new plugins - no conflicts)
- Thread Restore (independent epic)
- DAS Training (new service layer)

### Medium Independence (Coordination Needed)
- CQMT DAS Workflow + Workbench Fixes (both touch app.html but different sections)
- Conceptualizer + Workbench Fixes (different services but may share some code)

### Low Independence (Sequential Recommended)
- All workbench fixes (#63, #64, #66, #49) - grouped together since they touch same areas

## Recommended Parallel Setup

### Agent 1: Workbench Foundation
**Branch:** `feature/workbench-fixes`  
**Issues:** #63, #64, #66, #49  
**Focus:** Fix individual tables, renaming issues  
**Duration:** ~1-2 weeks

### Agent 2: New Workbenches (Parallel Stream A)
**Branches:** 
- `feature/configurator-workbench`
- `feature/tabularizer-workbench`  
**Focus:** Build plugins, validate architecture  
**Duration:** ~2-3 weeks each (can be parallel)

### Agent 3: New Workbenches (Parallel Stream B)
**Branch:** `feature/data-manager-workbench`  
**Issue:** #54  
**Focus:** Build data manager plugin  
**Duration:** ~2-3 weeks

### Agent 4: DAS Enhancements
**Branches:**
- `feature/thread-restore` (Epic #70)
- `feature/das-training-system` (Epic #67)
- `feature/cqmt-das-workflow` (#65)
**Focus:** DAS reliability and training  
**Duration:** Thread restore ~1 week, DAS training ~2-3 weeks

### Agent 5: Backend Services
**Branch:** `feature/conceptualizer-fuseki`  
**Issue:** #61  
**Focus:** Store individuals in Fuseki  
**Duration:** ~1 week

## Merge Coordination

### Merge Order (Minimize Conflicts)

1. **First Wave** (Week 1-2)
   - `feature/workbench-fixes` → main
   - `feature/conceptualizer-fuseki` → main

2. **Second Wave** (Week 3-4)
   - `feature/thread-restore` → main
   - `feature/cqmt-das-workflow` → main

3. **Third Wave** (Week 5-6)
   - `feature/configurator-workbench` → main
   - `feature/tabularizer-workbench` → main

4. **Fourth Wave** (Week 7-8)
   - `feature/data-manager-workbench` → main
   - `feature/das-training-system` → main (if complete)

### Merge Strategy
- Each branch merges to main independently
- No cross-branch merging (follows git workflow guidelines)
- Coordinate merges to minimize conflicts
- Test each merge before next one

## Conflict Avoidance

### File Ownership Zones

**Low Risk (Multiple agents can touch):**
- New plugin workbenches (completely new files)
- New services (new files)
- Independent features (different files)

**Medium Risk (Coordinate):**
- `frontend/app.html` - Multiple workbenches touch this
- `backend/main.py` - Multiple features add routes
- Shared services - Check before modifying

**High Risk (Single agent):**
- Workbench fixes (#63-#66) - All touch individual tables/ontology workbench
- Group these together

### Communication Protocol

**Before starting work:**
```bash
# Announce which files you'll be modifying
"I'll be working on feature/configurator-workbench
Files I'll create: frontend/js/workbenches/configurator/
No existing files modified"
```

**If touching shared files:**
```
"I need to modify backend/main.py to add configurator routes
Should I coordinate with other agents working on main.py?"
```

## Branch Naming Convention

```
feature/[component]-[descriptor]
Examples:
- feature/workbench-fixes
- feature/configurator-workbench
- feature/thread-restore
- feature/das-training-system
- feature/cqmt-das-workflow
```

## Daily Coordination

### Morning Standup (Metaphorical)
- Agent 1: "Working on workbench fixes, touching app.html lines 29000-30000"
- Agent 2: "Creating configurator plugin, new files only"
- Agent 3: "Thread restore, modifying backend/api/das2.py"
- **Result:** Coordinate if conflicts possible

### Conflict Detection
```bash
# Check what others are working on
gh pr list --state open

# Check if your branch conflicts with others
git fetch origin
git merge-base feature/my-branch origin/main
git diff origin/main...feature/my-branch --name-only
```

## Success Criteria

**Parallel Work Success:**
- ✅ 4-6 branches active simultaneously
- ✅ Minimal merge conflicts
- ✅ CI passes for each branch
- ✅ Clean squash-merge to main
- ✅ No cross-branch dependencies

**Coordination Success:**
- ✅ No simultaneous edits to same files
- ✅ Clear communication about file ownership
- ✅ Merges coordinated to minimize conflicts
- ✅ All branches merge cleanly to main

## Multi-Agent Coordination in Cursor

### Setting Up Parallel Agents

With multiple Cursor agents available, assign each agent a branch:

**Agent Assignments:**
```
Agent 1 → feature/workbench-fixes (#63, #64, #66, #49)
Agent 2 → feature/configurator-workbench (NEW plugin)
Agent 3 → feature/thread-restore (#70)
Agent 4 → feature/tabularizer-workbench (NEW plugin)
Agent 5 → feature/das-training-system (#67)
```

### Agent Communication Protocol

**Each agent should:**
1. Announce branch and scope at start
2. List files they'll modify
3. Check for conflicts before major commits
4. Coordinate merges to main

**Conflict Prevention:**
- Use branch prefixes: "Agent 1: Working on..." in commit messages
- Check `gh pr list` before modifying shared files
- Communicate if touching `app.html` or `main.py`

## Recommended Approach: **Parallel with Coordination**

**Start with:**
1. `feature/workbench-fixes` (Agent 1) - Single branch for related fixes
2. `feature/configurator-workbench` (Agent 2) - Independent new plugin
3. `feature/thread-restore` (Agent 3) - Independent epic

**Add as first complete:**
4. `feature/tabularizer-workbench` (Agent 2 or new)
5. `feature/das-training-system` (Agent 3 or new)

**Benefits:**
- ✅ Faster delivery (parallel work)
- ✅ Independent components (low conflict risk)
- ✅ Validates architecture with multiple plugins
- ✅ Clear ownership (each agent has clear scope)

---

*This strategy maximizes parallel development while maintaining git workflow best practices.*
