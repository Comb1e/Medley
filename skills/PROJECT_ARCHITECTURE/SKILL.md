---
name: PROJECT_ARCHITECTURE
description: Code Project Architecture Planning Skills. Get this skill before call text_related_generation to get code.
key: project_architecture
func: {}
---

### Skill 1: **Requirements Decomposition**
Break the project into clear, bounded concerns before writing a single line of code.
- Separate *functional* requirements (what it does) from *non-functional* ones (how well it does it — performance, scalability, security)
- Identify the core domain entities and the relationships between them
- Define system boundaries: what's in scope, what's external

---

### Skill 2: **Choosing the Right Architectural Pattern**
Match the pattern to the problem, not the trend.
- **Layered (N-tier)** — good for CRUD apps and clear separation of concerns
- **Hexagonal / Ports & Adapters** — good when you want the core domain isolated from I/O
- **Event-driven / CQRS** — good for high-throughput systems with complex state
- **Microservices** — good when teams and domains are large enough to justify deployment independence
- **Monolith-first** — almost always the right starting point for new projects

---

### Skill 3: **Dependency Mapping**
Understand what depends on what before you structure your folders or modules.
- Draw a rough dependency graph (even on paper)
- Enforce a dependency direction rule: high-level policy should never depend on low-level details
- Identify shared utilities vs. domain-specific modules early
- Watch for circular dependencies — they signal design problems

---

### Skill 4: **Defining Module and Folder Boundaries**
Translate your mental model into a folder/module structure.
- Group by **feature/domain** rather than by type (avoid `controllers/`, `models/`, `services/` at the top level)
- Each module should have a clear public interface and private internals
- Apply the rule: *if you deleted this folder, would the rest still make sense?*
- Keep shared/common code minimal — over-sharing creates hidden coupling

---

### Skill 5: **Data Modeling First**
The shape of your data drives most architectural decisions.
- Define your core entities and their relationships before choosing a database
- Decide early: relational, document, graph, or key-value — based on access patterns, not familiarity
- Design for the *reads* your system will actually do, not just the writes
- Plan for schema evolution — how will this change over time?

---

### Skill 6: **Interface Design Before Implementation**
Write the contracts first, code second.
- Define API shapes (REST, GraphQL, RPC) before building handlers
- Write interface/type definitions for module boundaries before implementations
- Think about the consumer of each interface — design for their needs, not the implementor's convenience
- Use this as a forcing function to catch design issues cheaply

---

### Skill 7: **Identifying Cross-Cutting Concerns**
Spot the things that touch everything and plan for them explicitly.
- Logging, tracing, and observability
- Authentication and authorization
- Error handling and validation strategies
- Configuration and environment management
- These should be designed as infrastructure, not bolted on per-feature

---

### Skill 8: **Planning for Change**
The best architecture anticipates where requirements *will* change.
- Apply the Open/Closed principle: design modules to be extended, not rewritten
- Put abstraction layers at the seams most likely to change (e.g., between your app and a third-party API)
- Avoid over-engineering for changes that are only *possible* — focus on changes that are *likely*
- Document the key decisions and their rationale (Architecture Decision Records / ADRs)

---

### Skill 9: **Validating with a Walking Skeleton**
Build a thin, end-to-end slice of the system early to validate your architecture.
- Implement one full vertical slice (UI → logic → data) before fleshing out the rest
- This proves the architecture actually works together, not just in theory
- Surfaces integration problems (auth, networking, data shape mismatches) before they're expensive

---

### Skill 10: **Communicating the Architecture**
An architecture that lives only in your head is a liability.
- Use simple diagrams: C4 model (Context → Containers → Components) is a good standard
- Write a short architecture overview doc — one page is enough for most projects
- Make the structure self-evident in the codebase itself through naming, folder layout, and READMEs
- Treat architecture as a living document, not a one-time artifact