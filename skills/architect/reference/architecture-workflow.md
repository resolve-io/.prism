# Architecture Workflow

Complete step-by-step guide for creating system architecture.

## Overview

The architect workflow follows a structured process from requirements to implementation planning, ensuring comprehensive, maintainable architecture that serves both technical and business needs.

## The 5-Phase Process

```
Requirements → Design → Document → Review → Plan
```

Each phase builds on the previous, with iterative refinement.

## Phase 1: Gather Requirements

### Objectives
- Understand the problem being solved
- Identify users and their needs
- Define functional and non-functional requirements
- Establish constraints and assumptions

### Activities

**1. User Journey Mapping**
- Who are the users?
- What are their goals?
- What workflows do they need?
- What pain points exist?

**2. Functional Requirements**
- Core features and capabilities
- User stories or use cases
- Business rules
- Data requirements

**3. Non-Functional Requirements**
- Performance (response time, throughput)
- Scalability (users, data, load)
- Security (authentication, authorization, data protection)
- Availability (uptime, disaster recovery)
- Maintainability (code quality, documentation)
- Compliance (GDPR, HIPAA, etc.)

**4. Constraints**
- Budget limitations
- Timeline requirements
- Technology constraints
- Team skills and capacity
- Legacy system integration

**5. Success Criteria**
- How will we measure success?
- What are the KPIs?
- What defines "done"?

### Outputs
- Requirements document
- User journey maps
- Success metrics
- Constraints list

### Tips
✅ Start with user needs, not technology
✅ Quantify non-functional requirements (not "fast" but "< 200ms")
✅ Identify must-have vs. nice-to-have
✅ Document assumptions explicitly

---

## Phase 2: Design System

### Objectives
- Choose appropriate technologies
- Define system components
- Plan data architecture
- Design integration patterns
- Consider scalability and security

### Activities

**1. Technology Selection**
- Evaluate options for each layer
- Consider team experience
- Balance innovation and stability
- Justify choices with trade-offs

**2. Component Architecture**
- Identify major components/services
- Define responsibilities
- Plan communication patterns
- Consider boundaries and interfaces

**3. Data Architecture**
- Design data model
- Choose database(s)
- Plan data flow
- Consider data residency and privacy

**4. API Design** (if applicable)
- RESTful or GraphQL
- Endpoint structure
- Authentication/authorization
- Versioning strategy

**5. Infrastructure Planning**
- Cloud provider and services
- Deployment architecture
- Scaling strategy
- Disaster recovery

**6. Security Architecture**
- Defense-in-depth strategy
- Authentication/authorization
- Data encryption
- Network security
- Compliance requirements

**7. Performance Optimization**
- Caching strategy
- Database optimization
- CDN usage
- Async processing

### Outputs
- System architecture diagram
- Component descriptions
- Technology stack definition
- Data model/schema
- API specification
- Infrastructure plan

### Tips
✅ Choose boring technology where possible
✅ Design for simplicity first, optimize later
✅ Consider developer experience
✅ Plan for monitoring and observability
✅ Document trade-offs and alternatives considered

---

## Phase 3: Document Architecture

### Objectives
- Create comprehensive, maintainable documentation
- Enable team understanding
- Support implementation
- Provide reference for future changes

### Activities

**1. Architecture Document Structure**

```markdown
# System Architecture: [Project Name]

## 1. Overview
- System purpose
- Key requirements
- Success criteria

## 2. Architecture Decisions
- Technology choices
- Justifications and trade-offs
- Alternatives considered

## 3. Component Architecture
- System diagram
- Component descriptions
- Communication patterns

## 4. Data Architecture
- Data model
- Database choices
- Data flow

## 5. API Design
- Endpoints
- Authentication
- Versioning

## 6. Infrastructure
- Cloud architecture
- Deployment strategy
- Scaling plan

## 7. Security
- Security architecture
- Authentication/authorization
- Compliance

## 8. Performance
- Performance targets
- Optimization strategies
- Monitoring plan

## 9. Implementation Plan
- Phases and milestones
- Dependencies
- Risk assessment

## 10. References
- Additional docs
- External resources
```

**2. Diagrams**

Create visual representations:
- System architecture diagram
- Component interaction diagram
- Data flow diagram
- Deployment architecture diagram
- Sequence diagrams (for critical flows)

**3. Decision Log**

Document key decisions:
```markdown
### Decision: [Technology/Pattern Choice]
**Date**: 2025-10-22
**Context**: [Why this decision was needed]
**Options Considered**:
1. Option A - [Pros/Cons]
2. Option B - [Pros/Cons]
**Decision**: Option B selected
**Rationale**: [Why Option B]
**Consequences**: [Trade-offs accepted]
```

### Outputs
- Complete architecture document
- Architecture diagrams
- Decision log
- API specifications
- Database schemas

### Tips
✅ Write for future you (6 months from now)
✅ Include "why" not just "what"
✅ Use diagrams liberally
✅ Keep it in version control
✅ Make it searchable

---

## Phase 4: Review & Validate

### Objectives
- Ensure architecture quality
- Identify gaps or issues
- Get team alignment
- Validate against requirements

### Activities

**1. Quality Checklist**

Run through architecture checklist:
```
execute-checklist architect-checklist
```

Areas to review:
- Requirements coverage
- Technology choices
- Security posture
- Performance considerations
- Scalability plan
- Cost implications
- Team capability alignment

**2. Peer Review**

Get feedback from:
- Senior engineers
- Security team
- Operations/DevOps
- Product team
- Other stakeholders

**3. Validate Against Requirements**

Cross-check:
- All functional requirements addressed?
- Non-functional requirements met?
- Constraints respected?
- Success criteria achievable?

**4. Risk Assessment**

Identify risks:
- Technical risks
- Timeline risks
- Resource risks
- Integration risks
- Operational risks

For each risk:
- Likelihood (Low/Medium/High)
- Impact (Low/Medium/High)
- Mitigation strategy

**5. Cost Analysis**

Estimate costs:
- Infrastructure costs (monthly)
- Development costs (time)
- Operational costs
- Total Cost of Ownership (TCO)

### Outputs
- Review feedback
- Updated architecture document
- Risk register
- Cost estimate
- Sign-off from stakeholders

### Tips
✅ Be open to feedback
✅ Challenge assumptions
✅ Consider "what if" scenarios
✅ Don't over-engineer
✅ Balance ideal vs. practical

---

## Phase 5: Plan Implementation

### Objectives
- Break architecture into implementable pieces
- Define phases and milestones
- Establish development roadmap
- Set team up for success

### Activities

**1. Shard Architecture**

Break into phases:
```
shard-prd
```

Considerations:
- Dependencies between components
- Risk mitigation (hardest first?)
- Value delivery (highest value first?)
- Team capacity
- Learning curve

**2. Define Milestones**

For each phase:
- Deliverables
- Success criteria
- Timeline estimate
- Dependencies
- Team assignment

**3. Create Development Roadmap**

```
Phase 1: Foundation (Weeks 1-4)
├── Database setup
├── Basic API structure
├── Authentication
└── Deployment pipeline

Phase 2: Core Features (Weeks 5-10)
├── Feature A
├── Feature B
└── Integration testing

Phase 3: Advanced Features (Weeks 11-14)
├── Feature C
├── Performance optimization
└── Security hardening

Phase 4: Launch Prep (Weeks 15-16)
├── Load testing
├── Documentation
└── Production readiness
```

**4. Define Success Metrics**

For each phase:
- What metrics indicate success?
- How will we measure?
- What are the thresholds?

**5. Plan Monitoring & Operations**

- Logging strategy
- Metrics collection
- Alerting rules
- Incident response plan
- Runbooks

### Outputs
- Implementation phases
- Development roadmap
- Milestone definitions
- Success metrics
- Monitoring plan

### Tips
✅ Start simple, iterate
✅ Deliver value incrementally
✅ Plan for learning and adaptation
✅ Include buffer time
✅ Celebrate milestones

---

## Common Workflows

### New Greenfield System

```
1. Gather requirements (Phase 1)
2. Design from scratch (Phase 2)
3. Document comprehensively (Phase 3)
4. Review with team (Phase 4)
5. Plan phased implementation (Phase 5)
```

### Brownfield Modernization

```
1. Document current system
2. Identify problems and constraints
3. Design target architecture
4. Plan migration strategy (strangler fig, etc.)
5. Define phased migration
6. Execute phase by phase
```

### API Design

```
1. Identify resources and operations
2. Design RESTful endpoints or GraphQL schema
3. Define authentication/authorization
4. Plan versioning strategy
5. Document API specification
6. Review with consumers
7. Implement and test
```

### Microservices Architecture

```
1. Identify business domains (DDD)
2. Define service boundaries
3. Plan inter-service communication
4. Design data strategy (per-service DBs)
5. Plan deployment and orchestration
6. Implement service by service
```

---

## Tools & Resources

### Diagramming
- Mermaid (text-based, version-controllable)
- Lucidchart
- Draw.io
- PlantUML

### Documentation
- Markdown in git repository
- Confluence
- Notion
- GitHub/GitLab wikis

### API Documentation
- OpenAPI/Swagger
- GraphQL introspection
- Postman collections

### Architecture Decision Records (ADR)
```markdown
# ADR-001: Use PostgreSQL for Primary Database

## Status
Accepted

## Context
We need a reliable, ACID-compliant database...

## Decision
We will use PostgreSQL...

## Consequences
- Pros: ...
- Cons: ...
```

---

## Red Flags to Watch For

❌ **Over-engineering**: Solving problems you don't have yet
❌ **Under-engineering**: Ignoring known scale/security needs
❌ **Technology resume building**: Choosing tech to learn, not to solve
❌ **Ignoring constraints**: Designing beyond budget/timeline
❌ **Skipping documentation**: Future you will regret it
❌ **No monitoring plan**: You can't fix what you can't see
❌ **Ignoring team skills**: Designing beyond team capability
❌ **No migration plan**: Can't get from here to there

---

## Quick Reference

### Creating Architecture Document

```
# Intelligent architecture creation - adapts to your project type
create-architecture

# The command will:
# 1. Analyze your PRD (docs/prd.md)
# 2. Determine if project is full-stack, backend-only, or frontend-only
# 3. Recommend appropriate template
# 4. Get your confirmation
# 5. Create comprehensive architecture documentation
```

### Getting Jira Context

```
jira PROJ-123
```

### Running Quality Check

```
execute-checklist
```

### Breaking into Phases

```
shard-prd
```

---

**Last Updated**: 2025-10-22
**Version**: 1.0.0
