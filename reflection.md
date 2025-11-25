# Reflection — Module 12
# Author: Roopesh Kumar Reddy Kaipa
# Date: 24/11/2025
In this module I implemented user registration/login flows and the calculation endpoints, keeping controllers thin and placing validation and computation in the model and schema layers. The `User` model and its hashing utilities were reused by the auth endpoints, and the calculation factory encapsulated creation rules so route handlers only orchestrate request parsing and persistence.

Running integration tests with `pytest` together with Docker Compose gave me strong assurances that endpoints remain reliable. Exercising disposable Postgres and Redis services caught issues that unit tests missed: startup ordering, connection timing, and realistic transactional behaviour. These tests also validated the interaction between JWT issuance and Redis-based revocation, which is critical for logout semantics.

Schemas from Modules 10–11 translated directly into route-level behavior: field and model validators enforced constraints (for example, preventing division by zero), provided consistent error messages, and cleaned incoming payloads before persistence. Database patterns — explicit session handling, commits, and careful object replacement for polymorphic rows — meant updates were safe and predictable at the route level.

Problems faced during the work included intermittent test flakiness caused by environment differences (SQLite vs Postgres), a tricky SQLAlchemy warning when changing a calculation's polymorphic `type` in-place, and missing edge-case checks in some schema validators. To address the polymorphic warning I implemented a safe replace strategy for updates: create a new subclass instance, copy immutable fields (id, timestamps), compute the new result, insert it, and remove the old row. This avoids changing SQLAlchemy's `polymorphic_identity` in-place and eliminates the warning while preserving data continuity.

