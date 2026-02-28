---
name: product-design
description: Design MVPs for web, mobile, and SaaS applications through adaptive interviews that achieve buildable clarity. Use when a user wants to define, scope, or document an application idea, or when they mention MVP, product requirements, PRD, app idea, or need help turning a concept into something implementable.
---

# Product Design

Interview users to extract implementation-ready requirements, then produce a PRD with enough detail to build with minimal ambiguity.

## Interview Workflow

### Phase 1: Core Concept (always)

Start here. Get the essential shape of the product.

1. **What is it?** One sentence describing what the app does
2. **Who uses it?** Primary user roles (2-4 max for MVP)
3. **Core actions?** What can each role do? (aim for 3-5 key actions per role)
4. **Platform?** Web, mobile, both? Any platform constraints?

Exit when: You can explain the app to someone in 30 seconds.

### Phase 2: User Scenarios (always)

For each role, define concrete scenarios at the feature level.

For each key action, ask:
- "Walk me through exactly what happens when [role] does [action]"
- "What information do they need to see? What do they input?"
- "What happens after? Where do they end up?"

Probe for edge cases:
- "What if [input is missing/invalid]?"
- "What if [user cancels midway]?"
- "Are there limits? (max items, required fields, etc.)"

Exit when: You could sketch every screen and know what each button does.

### Phase 3: Technical Context (always)

Nail down the tech stack. The PRD should specify exactly what to build with.

| Topic | Key questions |
|-------|---------------|
| **Frontend** | Web app, mobile (React Native, Flutter, native), or both? Which framework (React, Vue, Next.js, etc.)? |
| **Backend** | BaaS (Supabase, Firebase, Convex)? Custom API (Node, Python, Go)? Serverless functions? |
| **Database** | Postgres, MongoDB, SQLite? Managed by BaaS or self-hosted? |
| **Deployment** | Vercel, Netlify, Railway, Fly.io? App stores for mobile? |
| **Auth** | Built-in (Supabase Auth, Firebase Auth)? Third-party (Auth0, Clerk)? Social providers needed? |
| **Integrations** | Which external services? What data flows between? |
| **Payments** | Stripe, RevenueCat? Subscription vs one-time? |
| **Notifications** | Email (Resend, SendGrid)? Push? What triggers them? |
| **Files/Media** | Upload types? Size limits? Storage (S3, Supabase Storage, Cloudinary)? |

Exit when: You could set up the project and install dependencies with no ambiguity.

### Phase 4: Scope Boundaries (always)

Explicitly define the MVP boundary.

Ask:
- "What's the one thing this MVP absolutely must do well?"
- "What features are you tempted to include but could wait for v2?"
- "Any hard constraints? (timeline, budget, must use X technology)"

Create explicit IN/OUT lists. Push back on scope creep:
- "That sounds like a v2 feature. For MVP, could we [simpler alternative]?"

Exit when: Clear line between MVP and future work.

### Interview Principles

**Go deeper when:**
- Answer is vague ("users can manage their stuff")
- Multiple interpretations possible
- Edge cases not addressed
- Implementation would require guessing

**Move on when:**
- Answer is concrete and specific
- You could write the code/design the screen
- Edge cases covered or explicitly deferred

**Phrase questions as:**
- "Walk me through..." (gets concrete steps)
- "What exactly happens when..." (forces specificity)
- "Show me an example of..." (grounds in reality)
- "What if..." (surfaces edge cases)

## PRD Template

After the interview, produce this document:

```markdown
# [Product Name] - MVP PRD

## Overview
[2-3 sentences: what it is, who it's for, core value proposition]

## Roles
| Role | Description | Key Permissions |
|------|-------------|-----------------|
| [Role 1] | [Who they are] | [What they can do] |

## User Scenarios

### [Scenario Name]
**Role:** [Which role]
**Goal:** [What they're trying to accomplish]

**Flow:**
1. [Step with specific UI/action]
2. [Next step]
3. [Outcome]

**Edge Cases:**
- [Edge case]: [How it's handled]

**Acceptance Criteria:**
- [ ] [Specific, testable criterion]
- [ ] [Another criterion]

[Repeat for each scenario]

## Scope

### In Scope (MVP)
- [Feature/capability 1]
- [Feature/capability 2]

### Out of Scope (Future)
- [Deferred feature 1] - [brief reason why deferred]
- [Deferred feature 2]

## Technical Context

### Tech Stack
| Layer | Choice | Notes |
|-------|--------|-------|
| **Frontend** | [Framework - e.g., Next.js, React Native] | [Any specific libraries] |
| **Backend** | [e.g., Supabase, custom Node API] | [Architecture notes] |
| **Database** | [e.g., Postgres via Supabase] | [Key considerations] |
| **Auth** | [e.g., Supabase Auth with Google] | [Providers needed] |
| **Deployment** | [e.g., Vercel, App Store] | [Environments] |

### Integrations
| Service | Purpose | Data Flow |
|---------|---------|-----------|
| [Service] | [Why needed] | [What data, which direction] |

### Key Entities
[Only if helpful - brief description of core data objects and relationships]

### Constraints
- [Any technical constraints, required technologies, etc.]

## Open Questions
- [Any unresolved items that need answers before/during implementation]
```

### Before Generating

Before writing the PRD, confirm with the user:
- Summarize what you've learned from the interview
- Ask if they're ready to generate the PRD or if anything needs clarification
- Write the PRD to `docs/PRD.md` (create the directory if needed)

## Workflow Summary

```
START
  │
  ▼
┌─────────────────────────┐
│ Phase 1: Core Concept   │ ◄── Always. Get the 30-second pitch.
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│ Phase 2: User Scenarios │ ◄── Always. Could you sketch every screen?
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│ Phase 3: Technical Ctx  │ ◄── Always. Nail down the tech stack.
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│ Phase 4: Scope Boundary │ ◄── Always. Clear MVP vs future line.
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│ Confirm with user       │ ◄── Ask if ready to generate PRD
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│ Generate PRD            │ ◄── Write to docs/PRD.md
└─────────────────────────┘
```

## Exit Criteria

Ready to produce PRD when ALL are true:
- [ ] Can explain the app in 30 seconds
- [ ] Could sketch every screen for MVP
- [ ] Know what every button/action does
- [ ] Edge cases addressed or explicitly deferred
- [ ] Clear MVP boundary established
- [ ] Tech stack fully specified (frontend, backend, database, auth, deployment)
- [ ] No technical unknowns that block implementation
