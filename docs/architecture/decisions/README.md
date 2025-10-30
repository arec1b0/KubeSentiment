# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records (ADRs) for the KubeSentiment project.

## What is an ADR?

An Architecture Decision Record (ADR) is a document that captures an important architectural decision made along with its context and consequences.

## ADR Format

Each ADR follows this structure:

1. **Title**: Short description of the decision
2. **Status**: Proposed, Accepted, Deprecated, or Superseded
3. **Context**: The issue motivating this decision
4. **Decision**: The change we're proposing or have agreed to
5. **Consequences**: What becomes easier or more difficult to do

## Index of ADRs

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [001](001-use-onnx-for-model-optimization.md) | Use ONNX for Model Optimization | Accepted | 2024-01-15 |
| [002](002-use-redis-for-distributed-caching.md) | Use Redis for Distributed Caching | Accepted | 2024-01-20 |
| [003](003-use-kafka-for-async-processing.md) | Use Kafka for Async Message Processing | Accepted | 2024-02-01 |
| [004](004-use-fastapi-as-web-framework.md) | Use FastAPI as Web Framework | Accepted | 2024-01-10 |
| [005](005-use-helm-for-kubernetes-deployments.md) | Use Helm for Kubernetes Deployments | Accepted | 2024-01-25 |
| [006](006-use-hashicorp-vault-for-secrets.md) | Use HashiCorp Vault for Secrets Management | Accepted | 2024-02-10 |

## Creating New ADRs

When creating a new ADR:

1. Create a new file named `NNN-title-with-dashes.md`
2. Use the next available number (NNN)
3. Follow the ADR template below
4. Update this index

### ADR Template

```markdown
# ADR NNN: [Title]

**Status:** [Proposed | Accepted | Deprecated | Superseded]
**Date:** YYYY-MM-DD
**Authors:** [Names]
**Supersedes:** [ADR number if applicable]

## Context

[Describe the issue or challenge that requires a decision]

## Decision

[Describe the decision that was made]

## Consequences

### Positive

- [List positive outcomes]

### Negative

- [List negative outcomes or trade-offs]

### Neutral

- [List neutral impacts]

## Alternatives Considered

- **Alternative 1:** [Description and why it was rejected]
- **Alternative 2:** [Description and why it was rejected]

## References

- [Links to relevant documentation, RFCs, discussions, etc.]
```

## References

- [Architecture Decision Records (ADR) by Michael Nygard](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
- [ADR GitHub Organization](https://adr.github.io/)
