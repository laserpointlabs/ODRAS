# DAS Architecture and Implementation Plan

## 🎯 **Overview**

This document outlines the comprehensive architecture and implementation plan for the Digital Assistance System (DAS) with proper session thread intelligence, activity tracking, and autonomous execution capabilities.

## 📝 **Terminology Clarification**
**session_thread_id**: LLM-style conversation thread containing ALL user activity for a work session (not web session)
- Similar to ChatGPT conversation threads
- Contains user actions, DAS interactions, context changes
- Discrete per login session, embedded for cross-thread learning

**⚠️ Future Reference**: When terminology confusion occurs, it's likely due to overlapping terms (e.g., "session" meaning both web sessions and LLM conversation threads). Always clarify the specific context and use precise terminology.

---

## 🏗️ **Core Architecture Components**

### **1. Session Thread Management**
```
User Login → NEW session_thread_id created (UUID) + linked to username
├── Each login = new session thread (threads do NOT persist across logins)
├── session_thread_id + username + metadata (session_goals, start_time, end_time, project_id)
├── Thread analytics: duration, goals achieved, work summary
├── Cross-thread learning via username linkage in metadata
└── Thread context maintained in Redis for duration of work session
```

### **2. Session Thread Content**
```
session_thread_id (UUID) → contains ALL work session activity
├── User Events: ontology creation, file uploads, ALL API calls
├── DAS Interactions: questions asked, commands executed, responses
├── Context Events: workbench switches, project selection, goal setting
├── Thread Metadata: username, start_time, end_time, session_goals, project_id changes
├── Thread Analytics: duration, productivity metrics, goal completion
└── Thread embedded in session_threads vector collection for cross-thread learning
```

### **3. Cross-User Intelligence & Learning**
```
Multi-User Session Analysis:
├── DAS sees patterns across ALL users (jdehart, admin, etc.)
├── Cross-user learning: "Users typically do X after creating Y"
├── Success/failure pattern recognition
├── Best practice identification from user behavior
├── Scoring mechanism: "don't do this" vs "definitely do this"
└── System-wide optimization suggestions
```

### **4. Event Capture & Processing**
```
User Action → Redis Queue → Background Summarization → session_thread collection
├── ALL events queued: API calls, UI clicks, DAS interactions
├── Background grouping: Take N events and summarize
├── DAS-triggered summarization: "summarizing current session work"
├── Priority queue: User requests immediate knowledge commitment
└── Comprehensive searchable session history
```

### **5. Enhanced RAG Query Process (Same Pipeline!)**
```
DAS Query → SAME rag_query_process workflow (extensible!)
├── Search: requirements collection
├── Search: knowledge collection  
├── Search: das_instructions collection (API commands)
├── Search: user_instructions collection (user guidance)
├── Search: session_thread collection (session memory)
└── Fallback: Direct LLM for natural conversation
```

### **6. Dual Instruction System**
```
das_instructions collection:
├── CURL examples for EVERY ODRAS endpoint
├── Parameter extraction patterns
├── Autonomous execution templates
└── "How DAS executes commands"

user_instructions collection:
├── Step-by-step user guidance
├── How-to tutorials and procedures
├── Educational content
└── "How DAS instructs users"
```

---

## 📋 **Implementation Tasks**

### **Phase 1: Session Thread Foundation**

#### **Task 1.1: Session Thread Management**
- [ ] Create NEW session_thread_id (UUID) on each user login
- [ ] Link session_thread_id to username in thread metadata
- [ ] Capture thread analytics: start_time, end_time, duration, goals
- [ ] Implement session goal capture (optional): "What do you want to accomplish?"
- [ ] Test thread lifecycle: login → work → logout → thread summary

#### **Task 1.2: Session Thread Collection**
- [ ] Create `session_threads` Qdrant collection (384 dimensions)
- [ ] Design comprehensive thread event schema with metadata
- [ ] Implement session thread embedding service
- [ ] Add thread search capabilities to RAG process

#### **Task 1.3: Comprehensive Event Capture**
- [ ] Create Redis event queue: `user_actions`
- [ ] **API Middleware Approach**: Add FastAPI middleware to log ALL API calls
  - Captures every request/response automatically
  - Includes debugging benefits (comprehensive API logging)
  - Published to Redis queue for background processing
  - Alternative: Direct integration into each API endpoint
- [ ] Integrate event capture into main APIs:
  - `backend/api/ontology.py` - ontology operations
  - `backend/api/files.py` - file operations  
  - `backend/api/projects.py` - project operations
- [ ] Add frontend event triggers for UI actions (button clicks, workbench switches)

#### **Task 1.4: Background Event Processing**
- [ ] Implement background event summarization service
- [ ] Design event grouping strategy (N events per summary)
- [ ] Create priority queue for immediate knowledge commitment
- [ ] Test Redis → Summarization → Embedding pipeline

### **Phase 2: Dual Instruction Collections**

#### **Task 2.1: Populate das_instructions Collection**
- [ ] Create CURL examples for EVERY ODRAS endpoint
- [ ] Add parameter extraction patterns for each API
- [ ] Include response handling templates
- [ ] Test autonomous command execution

#### **Task 2.2: Create user_instructions Collection**
- [ ] Build step-by-step user guidance content
- [ ] Add how-to tutorials and procedures
- [ ] Include educational content for ODRAS features
- [ ] Test DAS user instruction capabilities

#### **Task 2.3: Extend RAG Query Process (Same Pipeline!)**
- [ ] Add session_thread collection to existing `rag_query_process`
- [ ] Add user_instructions collection to search
- [ ] Implement collection search priority/weighting
- [ ] Add direct LLM fallback when no vector hits
- [ ] Test unified RAG pipeline with all collections

### **Phase 3: Cross-User Intelligence**

#### **Task 3.1: Multi-User Pattern Recognition**
- [ ] Implement cross-user session analysis
- [ ] Design success/failure scoring mechanism
- [ ] Add pattern recognition for common workflows
- [ ] Create best practice identification system

#### **Task 3.2: Dynamic Knowledge Commitment**
- [ ] Implement user-triggered knowledge commitment
- [ ] Add conversation → knowledge asset conversion
- [ ] Create priority queue for immediate processing
- [ ] Test "commit our discussion to knowledge" functionality

#### **Task 3.3: System-Wide Learning**
- [ ] Enable DAS to learn from all user mistakes/successes
- [ ] Implement recommendation system based on user patterns
- [ ] Add proactive suggestions based on cross-user analysis
- [ ] Create feedback loop for continuous improvement

### **Phase 3: Session Intelligence**

#### **Task 3.1: Real-time Session Awareness**
- [ ] Integrate session event capture into main APIs:
  - `backend/api/ontology.py` - ontology operations
  - `backend/api/files.py` - file operations
  - `backend/api/projects.py` - project operations
- [ ] Add frontend event triggers for UI actions
- [ ] Implement session context updates

#### **Task 3.2: DAS Session Intelligence**
- [ ] Enable DAS to query session_thread collection
- [ ] Implement context-aware responses
- [ ] Add proactive suggestion system
- [ ] Design session goal tracking

#### **Task 3.3: Autonomous Command Execution**
- [ ] Populate das_instructions with executable commands
- [ ] Test command recognition and execution
- [ ] Implement session-aware parameter extraction
- [ ] Add command execution logging to session thread

---

## ✅ **Architectural Decisions Made**

### **1. Session Management Strategy**
**Decision**: Simple UUID sessions with rich metadata embedding
- session_id: Simple UUID (no data in designator name)
- Metadata embedded: username, start_time, end_time, project_id, etc.
- Project_id can change during session (captured in events)
- Cross-session linking via username in metadata, not session naming

### **2. Event Capture Scope**
**Decision**: Capture ALL user actions
- API calls (ontology creation, file uploads)
- UI interactions (button clicks, workbench switches)
- DAS interactions (questions, commands, responses)
- System events (workflow completion, analysis results)

### **3. Cross-User Intelligence Scope**
**Decision**: Full cross-user and cross-project learning
- DAS sees patterns across ALL users (jdehart, admin, etc.)
- Cross-project pattern recognition (users have multiple projects)
- System-wide usage analysis and optimization
- Security considerations deferred to later implementation

### **4. RAG Integration Strategy**
**Decision**: Use existing `rag_query_process` workflow (NO fallback!)
- Extend with session_thread collection search
- Add user_instructions collection
- Keep single unified RAG pipeline
- NO LLM fallback - errors expose broken parts that need fixing

### **5. Event Processing Strategy**
**Decision**: LLM-driven intelligent summarization
- Start with 10-20 events per summary group (adjustable)
- **LLM-Determined Grouping**: Ask LLM to analyze event queue and determine optimal summary points
- DAS-triggered immediate summarization on user request
- Priority queue for "commit to knowledge" requests  
- Keep ALL session data forever (comprehensive learning dataset)
- Cross-user and cross-project analysis for pattern recognition

### **6. Instruction Collections Strategy**
**Decision**: Dual collection approach
- `das_instructions`: CURL examples for autonomous execution
- `user_instructions`: Guidance content for user education  
- Both searchable via same RAG process

### **7. Enhanced Semantic Logging Strategy**
**Decision**: Leverage existing Uvicorn logging with semantic enhancement
- **Current Logs**: Basic HTTP format (`"PUT /api/ontology/layout?graph=..." 200 OK`)
- **Enhanced Semantics**: Extract meaningful actions for session intelligence
- **Semantic Events**: Rich context with project_id, ontology_id, workbench context
- **Redis Queuing**: Clean, semantic events queued for background processing

**Example Enhancement**:
```
Current Log: "PUT /api/ontology/layout?graph=...bseo-v1 HTTP/1.1" 200 OK

Enhanced Semantic Event:
{
  "semantic_action": "Modified layout for ontology bseo-v1",
  "context": {"ontology_id": "bseo-v1", "project_id": "caee53ce..."},
  "metadata": {"workbench": "ontology", "action_type": "layout_modification"}
}
```

**Benefits**: 
- Builds on existing robust logging infrastructure
- Adds semantic meaning for DAS intelligence
- Enables context-aware responses ("that ontology" = "bseo-v1")
- Clean, structured events for session thread embedding

### **8. No Fallback Philosophy**
**Decision**: Errors expose broken parts, no LLM fallbacks
- When RAG fails, show clear error (don't hide with fallback)
- Forces proper implementation of vector collections
- Ensures DAS capabilities are built on solid foundations
- Fallbacks hide problems and prevent proper development

### **9. SME Feedback Learning (Stretch Goal)**
**Architecture**: Simple feedback collection with pattern recognition
- **Feedback Collection**: SMEs rate DAS responses (1-5 stars + comments)
- **Feedback Storage**: Stored with response context in session_threads
- **Pattern Recognition**: DAS searches previous feedback for similar situations
- **Behavior Adjustment**: DAS references past SME corrections in future responses
- **Knowledge Integration**: SME corrections become searchable knowledge

**Implementation**:
```
DAS Response → SME Feedback UI → Feedback stored in session_thread
├── Feedback metadata: SME_id, rating, comments, response_context
├── Future queries: DAS searches for similar feedback patterns
├── Response enhancement: "Based on SME feedback, I should also mention..."
└── Knowledge creation: High-rated SME corrections → knowledge assets
```

---

## 🧪 **Testing Strategy**

### **Test Scenario 1: Cross-Thread Learning**
```
Thread 1 (jdehart): Creates ontology "aircraft_systems" → captured in session_threads collection
Thread 2 (jdehart): "what ontologies have I created?"
Expected: DAS searches session_threads → finds "aircraft_systems" from previous thread
```

### **Test Scenario 2: Autonomous Command Execution**
```
User: "create a new project called test-navigation"
Expected: 
1. DAS searches das_instructions → finds "create_project" with CURL example
2. Extracts parameters: name="test-navigation"
3. Executes: POST /api/projects via das_service account
4. Captures execution in session_thread
5. Responds: "✅ Created project 'test-navigation' (project_id: xyz)"
```

### **Test Scenario 3: Session Memory & Context**
```
User: Creates ontology class "AirVehicle" → captured in session_thread
User: "add a relationship to that class"
Expected: DAS searches session_thread → knows "that class" = "AirVehicle"
```

### **Test Scenario 4: Cross-User Learning**
```
Multiple users create projects → DAS learns common patterns
New user: "how do I start a new project?"
Expected: DAS provides guidance based on successful patterns from other users
```

### **Test Scenario 5: Dynamic Knowledge Commitment**
```
User has discussion with DAS about ontology design best practices
User: "That was great advice. Can you commit our discussion to knowledge?"
Expected: 
1. DAS summarizes current conversation
2. Creates knowledge asset from discussion
3. Embeds in knowledge collection
4. Confirms: "✅ Committed our ontology design discussion to knowledge base"
```

### **Test Scenario 6: No Fallback - Expose Broken Parts**
```
User: "hello, how are you?"
Expected: ERROR or clear indication that RAG system needs improvement
NOT: Fallback to LLM (which hides broken vector search)
Goal: Force proper implementation of conversational content in vector collections
```

### **Test Scenario 7: SME Feedback Learning (Stretch Goal)**
```
User: "What's the best approach for aircraft navigation requirements?"
DAS: Provides response based on current knowledge
SME: Rates response "Poor - missing critical safety considerations"
Future Similar Query: DAS references previous SME feedback
DAS: "Based on SME feedback, I should emphasize safety considerations for navigation requirements..."
```

---

## 📊 **Success Metrics**

### **Session Intelligence**
- [ ] **Event Capture**: 95%+ of user actions captured in Redis
- [ ] **Context Accuracy**: DAS correctly references recent user actions
- [ ] **Thread Searchability**: Session history searchable via vector similarity

### **Conversation Quality**
- [ ] **Natural Responses**: No robotic "no information found" responses
- [ ] **Context Awareness**: DAS references session context in responses
- [ ] **Goal Tracking**: Session goals captured and referenced

### **Autonomous Execution**
- [ ] **Command Recognition**: 85%+ accuracy for common commands
- [ ] **API Execution**: 95%+ successful autonomous command execution
- [ ] **Session Integration**: Commands logged in session thread

---

## 🚀 **Implementation Priority & Next Steps**

### **Immediate (Start Here)**
1. **Remove All Fallbacks**: Expose broken parts instead of hiding with fallbacks
2. **Simple UUID Session Threads**: session_thread_id as UUID + rich metadata embedding
3. **Session Thread Collection**: Create `session_threads` Qdrant collection  
4. **Populate das_instructions**: Add CURL examples for ALL ODRAS endpoints
5. **API Middleware**: Log all API calls to Redis for comprehensive event capture

### **Phase 1 (Foundation)**
1. **Background Event Capture**: Redis queue + API middleware for ALL user actions
2. **Event Summarization**: Background service to group and embed session events
3. **RAG Integration**: Add session_thread collection to `rag_query_process`
4. **Test Basic Session Intelligence**: DAS can reference recent user actions

### **Phase 2 (Intelligence)**
1. **Cross-User Learning**: Multi-user pattern recognition and scoring
2. **Dynamic Knowledge Commitment**: User-triggered conversation → knowledge conversion
3. **Comprehensive API Coverage**: CURL examples for every ODRAS endpoint
4. **Natural Conversation**: Full LLM integration for general chat

### **Phase 3 (Advanced)**
1. **Proactive Suggestions**: DAS suggests actions based on usage patterns
2. **Best Practice Learning**: Success/failure pattern recognition
3. **System Optimization**: DAS helps improve ODRAS workflows
4. **Cross-Thread Intelligence**: Long-term user behavior analysis

### **Phase 4 (Stretch Goal): SME Feedback Learning**
1. **User Role System**: Implement Admin, Domain SME, and User roles
2. **SME Feedback Collection**: Subject Matter Expert rating system for DAS responses
3. **Weighted Feedback**: SME feedback weighted higher than regular user feedback
4. **Feedback Integration**: DAS notices feedback patterns and adjusts behavior
5. **Expert Knowledge Integration**: SME corrections become part of DAS knowledge
6. **Continuous Improvement**: DAS references previous feedback for similar situations

---

## 🔧 **Technical Decisions Needed**

### **Before Implementation Starts:**

1. **Session Thread Schema**: Define event structure and metadata
2. **Collection Strategy**: Single RAG pipeline vs multiple specialized pipelines
3. **Embedding Frequency**: Real-time vs batched vs DAS-triggered
4. **Event Granularity**: Which user actions to capture
5. **LLM Integration**: How to handle general conversation fallback

### **Architecture Questions:**
- Should we modify existing `rag_query_process` or create new workflow?
- How to handle session thread search priority vs other collections?
- What's the optimal session summary and embedding strategy?
- How to implement cross-session learning and pattern recognition?

---

## 💡 **Next Steps**

1. **Review and Approve**: Review this plan and provide feedback
2. **Research Phase**: Investigate LLM thread management best practices
3. **Design Session Thread Schema**: Define event structure and metadata
4. **Prototype Core Components**: Start with session thread collection and basic event capture
5. **Test and Iterate**: Validate approach with real user scenarios

**Goal**: Build a truly intelligent DAS that understands session context and can execute commands autonomously, not a collection of canned responses and disconnected features.

---

## 📋 **Current Status**

### **✅ What's Working**
- DAS basic chat functionality
- Autonomous API execution framework (das_api_client.py)
- Command recognition system (das_command_engine.py)
- Multi-vector RAG access (das_rag_service.py)
- Secure service account (das_service)

### **❌ What Needs Fixing**
- Session thread collection and embedding
- Real session event capture from user actions
- LLM fallback for general conversation
- Integration with existing RAG query process
- Session-aware command execution

### **🎯 Priority Focus**
- Remove canned responses, implement proper LLM fallback
- Design and implement session thread architecture
- Integrate event capture into existing user action flows
- Test session intelligence with real user scenarios

**Ready for your review and feedback before proceeding with implementation.**
