# MVP vs Refactoring Strategy - ODRAS Development Plan

## Decision Context

**Current Situation:**
- ODRAS has working features but monolithic architecture
- MVP needs completion: CQMT cleanup, ontology fixes, conceptualizer improvements, configurator, tabularizer, data manager
- Refactoring needed: Plugin architecture, event bus, scalable workbench development

**Critical Blockers Identified:**
- #55: Backend refactoring (main.py is 3,764 lines)
- #56: Frontend refactoring (app.html is 31,522 lines)

## Recommended Strategy: **MVP-First with Incremental Refactoring**

### Approach: Complete MVP on Current Architecture While Building New Components in Refactored Pattern

**Rationale:**
1. **MVP Can Be Built Now** - Current architecture supports MVP features
2. **New Components = Refactored Architecture** - Build configurator, tabularizer, data manager as plugins/workbenches
3. **Incremental Debt Reduction** - Refactor existing code as you touch it
4. **Working System Faster** - Deliver MVP functionality while building foundation
5. **Validated Architecture** - Test refactored patterns with real workbenches

## Implementation Strategy

### Phase 1: MVP Completion (Primary Focus)
**Goal:** Complete ODRAS MVP with working features
**Timeline:** Next 6-8 weeks (expanded to include thread restore and DAS training)

**Tasks:**
1. **CQMT Workbench Cleanup**
   - Fix issues #63-#66 (migration, counts, etc.)
   - Complete DAS-driven workflow (#65)
   - Polish UI and functionality

2. **Ontology Workbench Improvements**
   - Fix individual count display (#63)
   - Resolve renaming issues (#64, #66)
   - Enhance usability

3. **Conceptualizer Enhancements**
   - Improve individual extraction
   - Better ontology guidance
   - Enhanced DAS prompts

4. **Thread Restore Functionality** (NEW)
   - Thread persistence and restore
   - Conversation history management
   - Thread state recovery
   - Project thread continuity
   - Critical for DAS workflow reliability

5. **DAS Training System** (#67 - Chat History Integration)
   - **Phase 1:** Chunking & knowledge extraction (conversation-aware)
   - **Phase 2:** Storage integration (SQL + Qdrant)
   - **Phase 3:** DAS integration (training on chat history)
   - **Phase 4:** Query interface ("How did we implement X?")
   - Train DAS on ODRAS build history/knowledge
   - Enable contextual development assistance

6. **Configurator Workbench** (NEW - Build as Plugin)
   - Build as first plugin/workbench module
   - Establishes refactored pattern
   - Validates plugin architecture approach

7. **Tabularizer Workbench** (NEW - Build as Plugin)
   - Second plugin/workbench module
   - Uses same refactored pattern
   - Generic table generation

8. **Data Manager Workbench** (NEW - Build as Plugin)
   - Requirements import to individuals table
   - Third plugin/workbench module
   - Validates data mapping patterns

**Success Criteria:** Complete MVP workflow functional end-to-end

### Phase 2: Incremental Refactoring (Parallel Track)
**Goal:** Refactor existing code as you touch it
**Timeline:** Ongoing alongside MVP

**Strategy:**
- **Refactor When You Touch** - When working on CQMT/ontology workbench fixes, refactor those modules
- **Extract to Modules** - Move touched code into plugin-style modules
- **Don't Big-Bang** - No full system refactor, just incremental improvement
- **Pattern Validation** - Use new workbenches (configurator, tabularizer) to validate refactored patterns

**Example:**
- Working on CQMT cleanup → Extract CQMT code to `workbenches/cqmt/` module
- Fixing ontology workbench → Extract ontology code to `workbenches/ontology/` module
- Each extraction becomes a plugin candidate

### Phase 3: Foundation Infrastructure (After MVP)
**Goal:** Complete refactoring foundation
**Timeline:** Post-MVP (Weeks 9-12, adjusted for expanded MVP scope)

**After MVP is Complete:**
1. **Complete Backend Refactoring** (#55)
   - Break up remaining main.py code
   - Plugin registry and loader
   - Service initialization

2. **Complete Frontend Refactoring** (#56)
   - Break up remaining app.html code
   - Core application modules
   - Component system

3. **Event Bus Implementation**
   - Event-driven architecture
   - Pub/sub system
   - Workbench communication

4. **Data Mapping via Ontologies**
   - Ontology-driven data transformation
   - Generic mapping engine
   - Integration with plugin system

## Why This Approach?

### Advantages:

1. **Delivers MVP Faster**
   - No waiting for refactoring
   - Users get working system sooner
   - Can validate MVP workflow

2. **Validates Architecture**
   - New workbenches test refactored patterns
   - Real-world usage validates design
   - Learn what works before full refactor

3. **Incremental Debt Reduction**
   - Technical debt reduced as you go
   - No big-bang refactor risk
   - Continuous improvement

4. **Lower Risk**
   - Working system always maintained
   - Can rollback incremental changes
   - MVP delivery not blocked

5. **Pattern Validation**
   - Build 3 new workbenches as plugins
   - Proves plugin architecture works
   - Establishes patterns for remaining workbenches

### Potential Concerns:

1. **"Will MVP Technical Debt Be Too High?"**
   - Answer: No - MVP features are mostly new (configurator, tabularizer, data manager)
   - Existing features (CQMT, ontology) get incremental refactoring as you fix them

2. **"Will Refactoring Take Longer?"**
   - Answer: Possibly, but MVP delivers value sooner
   - Incremental refactoring is actually safer than big-bang

3. **"Will We Duplicate Work?"**
   - Answer: Minimal - new workbenches build in refactored pattern
   - Existing workbenches refactor incrementally

## Workflow Integration

**Daily Work:**
- 70% time on MVP completion
- 30% time on incremental refactoring (as you touch code)

**Example Day:**
- Morning: Fix CQMT issue → Extract CQMT code to module (MVP + refactoring)
- Afternoon: Build configurator workbench as plugin (MVP + pattern validation)

## Success Metrics

**MVP Completion:**
- ✅ All MVP features working
- ✅ End-to-end workflow functional
- ✅ Users can complete full workflow
- ✅ Thread restore working reliably
- ✅ DAS trained on ODRAS knowledge base
- ✅ DAS provides contextual development assistance

**Refactoring Progress:**
- ✅ 3+ workbenches built as plugins
- ✅ Plugin architecture validated
- ✅ Incremental refactoring underway

**Technical Debt:**
- ✅ Monolithic files reduced in size
- ✅ New code follows refactored patterns
- ✅ Foundation ready for full refactor

**DAS Training:**
- ✅ Chat history integrated into knowledge base
- ✅ DAS can answer "How did we implement X?" questions
- ✅ Development patterns captured and searchable
- ✅ Context-aware suggestions during development

## Alternative: Full Refactor First

**If you chose full refactor first:**
- ⚠️ MVP delivery delayed 8-10 weeks
- ⚠️ No working system during refactor
- ⚠️ Architecture decisions untested
- ⚠️ Thread restore and DAS training delayed
- ✅ Clean architecture from start
- ✅ No technical debt

**Recommendation:** Only choose this if MVP timeline is flexible and you want perfect architecture first.

## Recommendation Summary

**✅ Proceed with MVP-First + Incremental Refactoring**

1. Complete MVP on current architecture
2. **Implement thread restore** for DAS workflow reliability
3. **Complete DAS training system** (#67) - integrate chat history into knowledge base
4. Build new workbenches (configurator, tabularizer, data manager) as plugins
5. Refactor existing workbenches incrementally as you fix/improve them
6. Complete full refactoring post-MVP when patterns are validated

**This gives you:**
- Working MVP faster (6-8 weeks vs 8-10+ weeks)
- Thread restore ensures DAS reliability
- DAS trained on ODRAS knowledge provides immediate value
- Validated architecture patterns
- Lower risk
- Continuous improvement

---

*Last Updated: October 31, 2025*
