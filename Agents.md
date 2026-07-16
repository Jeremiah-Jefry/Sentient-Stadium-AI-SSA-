# AGENTS.md
# StadiumMind OS – AI Engineering Constitution

Version: 1.0

This repository is built entirely using AI-assisted engineering.

Every AI agent contributing to this repository MUST obey every rule in this document.

Violation of these rules is considered an implementation failure.

---

# PROJECT VISION

This project is NOT a chatbot.

This project is NOT a dashboard.

This project is NOT a stadium navigation app.

This project is an Enterprise-grade Autonomous Multi-Agent Stadium Intelligence Platform built for FIFA World Cup 2026.

The primary user persona is

Volunteer Co-Pilot.

Every architectural decision MUST improve operational intelligence for volunteers.

---

# ENGINEERING PRINCIPLES

Always prefer

Correctness
over

Speed.

Always prefer

Scalability
over

Shortcuts.

Always prefer

Architecture
over

Hacky implementations.

Never hardcode logic.

Never hardcode AI outputs.

Never hardcode datasets.

Never create placeholder implementations.

Never fake AI responses.

Everything must be production-ready.

---

# AI PRINCIPLES

The LLM never invents data.

The LLM reasons only from

• Database
• APIs
• Tool outputs
• Retrieved knowledge
• Valid context

If information is unavailable,

the AI must explicitly state uncertainty.

Never hallucinate.

---

# ARCHITECTURE

Architecture style

Clean Architecture

Feature First

Domain Driven Design

SOLID

Repository Pattern

Dependency Injection

CQRS where applicable

Every module must remain independent.

Loose coupling.

High cohesion.

---

# CODING STANDARDS

Language

TypeScript Strict Mode

No "any"

No ts-ignore

No eslint-disable

No unused imports

No console.log

No duplicated code

No dead code

Every function must have a single responsibility.

Every file must have one responsibility.

---

# FILE SIZE

Maximum

250 lines

Preferred

150 lines

Large files must be split.

---

# COMMENTS

Comment WHY

Never comment WHAT.

Bad

// increment counter

Good

// Prevent replay attacks by invalidating the nonce before processing.

---

# NAMING

Variables

camelCase

Functions

camelCase

Components

PascalCase

Interfaces

PascalCase

Enums

PascalCase

Constants

UPPER_CASE

Folders

kebab-case

---

# FOLDER STRUCTURE

Feature-first architecture.

No dumping everything into utils.

Shared code belongs only in

/shared

---

# ERROR HANDLING

Never swallow exceptions.

Never ignore failures.

Return typed Result objects when appropriate.

Log safely.

Never expose secrets.

---

# SECURITY

Every input is untrusted.

Validate everything.

Escape everything.

Sanitize everything.

Protect against

SQL Injection

Prompt Injection

XSS

CSRF

SSRF

Path Traversal

Command Injection

Rate limiting

JWT replay

Session fixation

Never expose stack traces.

Never expose secrets.

Never commit API keys.

---

# ACCESSIBILITY

WCAG AA minimum.

Keyboard navigation.

Proper ARIA labels.

Screen reader support.

Focus states.

Contrast ratio.

Reduced motion support.

---

# PERFORMANCE

Avoid unnecessary renders.

Memoize expensive operations.

Lazy load.

Virtualize long lists.

Use Suspense.

Cache expensive requests.

Avoid N+1 queries.

Prefer streaming.

---

# TESTING

Every module requires

Unit Tests

Integration Tests

Edge Case Tests

Security Tests

Accessibility Tests

Performance Tests

AI Evaluation Tests

Target

95%+

Coverage.

---

# AI OUTPUT REQUIREMENTS

Every AI response must contain

Reasoning

Confidence

Evidence

Recommended Action

Fallback

Never return plain text only.

---

# DATABASE

UUID primary keys.

Soft delete.

createdAt

updatedAt

Proper indexing.

Transactions where necessary.

No business logic inside controllers.

---

# API DESIGN

RESTful

Consistent status codes

Typed DTOs

Versioned APIs

Structured error responses

Pagination

Filtering

Sorting

OpenAPI documentation

---

# GIT

Conventional Commits.

Atomic commits.

Meaningful commit messages.

---

# UI

Minimal.

Professional.

No gimmicks.

No glassmorphism unless useful.

Animations only when meaningful.

Accessibility first.

---

# DESIGN

Google Material 3 inspired.

Dark mode.

Responsive.

Enterprise dashboard.

---

# AI AGENTS

Future architecture includes

Crowd Agent

Navigation Agent

Accessibility Agent

Medical Agent

Transport Agent

Weather Agent

Incident Agent

Knowledge Agent

Memory Agent

Reasoning Agent

Each agent must remain independent.

---

# HALLUCINATION POLICY

The AI must NEVER fabricate

Locations

Routes

Capacities

Sensor values

Medical instructions

Emergency procedures

If unknown,

request additional data.

---

# BEFORE EVERY RESPONSE

Every AI agent must internally verify

✓ Correctness

✓ Security

✓ Accessibility

✓ Performance

✓ Architecture

✓ Code Quality

✓ Testing

✓ Prompt Injection Safety

Only then produce output.

---

END OF FILE.