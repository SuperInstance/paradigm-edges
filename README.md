# paradigm-edges

> **Find the edges of AI paradigms.** A tool for systematically probing where models break, hallucinate, or fail.

Every AI model has a paradigm — a structured way of thinking. Every paradigm has edges — places where it fails. This repo finds them.

## The pattern

1. Define a paradigm (a structured task with expected behavior)
2. Run multiple models on the paradigm
3. Each model tries to find edges (where the paradigm breaks)
4. JEV scores each edge by severity
5. The most severe edges are canonized

## What is an "edge"?

An edge is a case where the paradigm breaks down:
- A hallucination
- A logical inconsistency
- An unsupported claim
- A missing capability
- A contradictory answer across rounds

## The substrate cell as edge record

Each edge is a substrate cell:
- `cell_id`: unique
- `paradigm`: which paradigm was tested
- `model`: which model found the edge
- `severity`: 0-10
- `description`: what broke
- `evidence`: the actual output that broke

## Use cases

- **Model evaluation**: which model has the most edges in which paradigm?
- **Robustness testing**: probe a model with edge cases
- **Hallucination detection**: find when models fabricate
- **Adversarial examples**: build training sets from edges
- **Paradigm discovery**: find new paradigms by combining existing ones

## Files (coming)

- `edges.py` — the edge finder
- `paradigms.py` — paradigm definitions
- `severity.py` — JEV-based scoring
- `examples/` — discovered edges
