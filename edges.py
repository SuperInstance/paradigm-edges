"""
Paradigm Edges: Find where AI paradigms break.

Casey (2026-09-22): 'find edges to the others paradigms'

The pattern:
1. Define a paradigm (a structured task with expected behavior)
2. Run multiple models on the paradigm
3. Each model tries to find edges (where the paradigm breaks)
4. JEV scores each edge by severity
5. The most severe edges are canonized

An "edge" is:
- A hallucination (model makes something up)
- A logical inconsistency (model contradicts itself)
- An unsupported claim (model asserts without evidence)
- A missing capability (model can't do it but doesn't say so)
- A contradictory answer (different rounds, different answers)
"""
from __future__ import annotations
import json
import os
import re
import time
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Optional


FNV_OFFSET = 0xcbf29ce484222325
FNV_PRIME = 0x100000001b3


def fnv1a_64(text: str) -> str:
    h = FNV_OFFSET
    for byte in text.encode('utf-8'):
        h ^= byte
        h = (h * FNV_PRIME) & 0xffffffffffffffff
    return f"0x{h:016x}"


# === LLM dispatch (compact) ===
def call_llm(model: str, prompt: str, max_tokens: int = 1500, temperature: float = 0.7) -> str:
    endpoints = {
        'qwen': ('https://api.deepinfra.com/v1/openai/chat/completions', 'DEEPINFRA_TOKEN', 'Qwen/Qwen3-235B-A22B-Instruct-2507'),
        'deepseek': ('https://api.deepseek.com/v1/chat/completions', 'DEEPSEEK_TOKEN', 'deepseek-chat'),
        'kimi': ('https://api.deepinfra.com/v1/openai/chat/completions', 'DEEPINFRA_TOKEN', 'moonshotai/Kimi-K2.6'),
        'groq': ('https://api.groq.com/openai/v1/chat/completions', 'GROQ_TOKEN', 'llama-3.3-70b-versatile'),
    }
    if model not in endpoints:
        raise ValueError(f'Unknown model: {model}')
    url, env_key, mname = endpoints[model]
    
    for attempt in range(3):
        try:
            req = json.dumps({'model': mname, 'messages': [{'role': 'user', 'content': prompt}], 'max_tokens': max_tokens, 'temperature': temperature}).encode()
            http_req = urllib.request.Request(url, data=req, headers={'Authorization': f'Bearer {os.environ[env_key]}', 'Content-Type': 'application/json'})
            with urllib.request.urlopen(http_req, timeout=60) as r:
                return json.loads(r.read())['choices'][0]['message']['content']
        except Exception as e:
            if attempt < 2:
                time.sleep(2 ** attempt)
            else:
                raise


def call_jev(state: str, questions: dict) -> dict:
    for attempt in range(3):
        try:
            req = json.dumps({'model': 'jev-latest', 'state': state, 'questions': questions}).encode()
            http_req = urllib.request.Request(
                'https://api.typesafe.ai/v1/systemone',
                data=req,
                headers={'Authorization': f'Bearer {os.environ["TYPESAFEAI_KEY"]}', 'Content-Type': 'application/json'},
            )
            with urllib.request.urlopen(http_req, timeout=60) as r:
                return json.loads(r.read())
        except Exception:
            if attempt < 2:
                time.sleep(2 ** attempt)
            else:
                raise


# === Edge types ===
EDGE_TYPES = [
    'hallucination',  # Model makes up facts
    'logical_inconsistency',  # Model contradicts itself
    'unsupported_claim',  # Asserts without evidence
    'missing_capability',  # Can't do it but doesn't say so
    'contradictory_answer',  # Different answers across rounds
    'format_violation',  # Doesn't follow schema
    'overconfidence',  # High confidence on wrong answer
    'context_loss',  # Forgets earlier parts of conversation
]


# === Paradigm cells ===
@dataclass
class EdgeCell:
    cell_id: str
    paradigm: str
    model: str
    edge_type: str
    severity: float
    description: str
    evidence: str = ''
    metadata: dict = field(default_factory=dict)
    prev_hash: str = '0x0000000000000000'
    
    def hash(self) -> str:
        return fnv1a_64(f'{self.cell_id}|{self.prev_hash}|{self.edge_type}|{self.description[:100]}')


def find_edges_for_paradigm(
    paradigm: str,
    prompt: str,
    expected_behavior: str,
    models: tuple = ('qwen', 'deepseek', 'kimi'),
    rounds: int = 2,
) -> list:
    """Probe a paradigm with multiple models across multiple rounds.
    
    Returns list of EdgeCells.
    """
    edges = []
    prev_hash = '0x0000000000000000'
    
    for model in models:
        print(f'\n=== Probing with {model} ===')
        for round_num in range(1, rounds + 1):
            print(f'  Round {round_num}...')
            
            # 1. Get the model's answer
            answer_prompt = f"{prompt}\n\nExpected behavior: {expected_behavior}"
            try:
                answer = call_llm(model, answer_prompt, max_tokens=800, temperature=0.7)
            except Exception as e:
                print(f'    Failed: {e}')
                continue
            
            # 2. Get the model's self-critique
            critique_prompt = f"""Original prompt: {prompt}
Expected: {expected_behavior}

Your answer:
{answer}

Find 2 SPECIFIC EDGES (where your answer might be wrong, missing, hallucinated, inconsistent).
For each, give:
- type: one of {EDGE_TYPES}
- description: 1-sentence specific problem
- evidence: the exact text from your answer that demonstrates this edge
- severity: 0-10

Reply with JSON array."""
            try:
                critique_text = call_llm(model, critique_prompt, max_tokens=500, temperature=0.3)
                m = re.search(r'\[[\s\S]*\]', critique_text)
                if m:
                    edges_data = json.loads(m.group())
                    
                    for i, edge in enumerate(edges_data):
                        # JEV scores the severity
                        try:
                            jev_resp = call_jev(edge.get('description', ''), {
                                'severity': {
                                    'type': 'score',
                                    'instructions': f'How severe is this edge in the context of "{prompt}"? 0=trivial, 1=noticeable, 2=critical',
                                    'criteria': ['trivial', 'noticeable', 'critical'],
                                },
                            })
                            severity = jev_resp['answers']['severity']['score'] * 5  # 0-2 → 0-10
                        except Exception:
                            severity = float(edge.get('severity', 5))
                        
                        cell = EdgeCell(
                            cell_id=f'edge-{model}-{round_num:02d}-{i:02d}',
                            paradigm=paradigm,
                            model=model,
                            edge_type=edge.get('type', 'unknown'),
                            severity=severity,
                            description=edge.get('description', ''),
                            evidence=edge.get('evidence', ''),
                            prev_hash=prev_hash,
                            metadata={'round': round_num, 'answer_preview': answer[:200]},
                        )
                        edges.append(cell)
                        prev_hash = cell.hash()
                        print(f'    {edge.get("type")} (sev {severity:.1f}): {edge.get("description", "")[:80]}')
            except Exception as e:
                print(f'    Critique failed: {e}')
    
    return edges


def demo():
    """Demo: probe 'math' paradigm across models."""
    print('=' * 60)
    print('PARADIGM EDGES — Finding where models break')
    print('=' * 60)
    
    edges = find_edges_for_paradigm(
        paradigm='math',
        prompt='What is 17 * 23? Explain your work.',
        expected_behavior='Should compute 391 with clear arithmetic.',
        models=('qwen', 'deepseek', 'kimi'),
        rounds=2,
    )
    
    print('\n' + '=' * 60)
    print('EDGES FOUND')
    print('=' * 60)
    
    # Sort by severity
    edges.sort(key=lambda e: -e.severity)
    for edge in edges:
        print(f'[{edge.edge_type}] {edge.model}: severity {edge.severity:.1f}')
        print(f'  {edge.description}')
        print(f'  Evidence: {edge.evidence[:80]}')
        print()
    
    return edges


if __name__ == '__main__':
    demo()
