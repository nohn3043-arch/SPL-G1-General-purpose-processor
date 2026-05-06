# SPL-G1 General-Purpose Processor

## Overview

SPL-G1 is an experimental heterogeneous processor architecture built on the SPL-Core (Second-Perspective Logic) paradigm. It unifies the primary execution domains traditionally separated across CPU, GPU, and NPU hardware into a single, coherent fabric.  

Designed to match the logical paradigm of the Second-Perspective language and virtual world framework, it natively supports large-scale virtual world ecosystems, logic deduction, and scene rendering.

> **The era of narrative-driven computing ends here.**

## Core Architectural Principles

Instead of relying on constant external memory transfers, G1 performs **state-centric computation** directly inside its PIM (Processing-In-Memory) fabric. By minimizing redundant data movement, the architecture targets substantially lower energy overhead while maintaining high-throughput parallel execution and low-latency inference capabilities.

G1 introduces a **logic-evolution execution model**, in which computation is treated as a traceable state transition process rather than a transient dataflow pipeline.

## Architectural Goals

The G1 architecture is designed around four core objectives:

1. Unified general-purpose and accelerated compute  
2. In-memory logic evolution  
3. Deterministic state anchoring  
4. Causality-aware execution auditing  

The platform aims to support:  

- General-purpose scalar workloads traditionally handled by CPUs  
- Parallel stream and rendering workloads associated with GPUs  
- Low-latency neural inference and tensor execution commonly mapped to NPUs  

… within a shared execution fabric and unified state model.

## SPL-Core Execution Model

SPL-Core replaces conventional fetch-execute-writeback behavior with a state-driven execution cycle:

**ANCHOR → EVOLVE → AUDIT → STRIP**

| Stage | Description |
|-------|-------------|
| `ANCHOR` | Commits the active computation state into the immutable State Anchor region for deterministic recovery and verification |
| `EVOLVE` | Executes logic transformations directly inside the PIM array, reducing external memory traffic and synchronization overhead |
| `AUDIT` | Performs causal-weight tracing and execution verification across active logic states |
| `STRIP` | Removes non-essential execution influence weights through the NSM filtering layer to maintain state consistency |

## Core Components

| Component | Description |
|-----------|-------------|
| `G1_Top_Interface.v` | Top-level hardware interface contract between the G1 processing module and the Origin-01 motherboard platform |
| `ISA_Spec.json` | Native SPL-Core instruction definitions for scalar, tensor, and massively parallel execution workloads |
| `Verification_Root.pdl` | Formal verification protocol for the 128MB State Anchor region; root verification hash: `8525d007` |

Supported primitive operations include: `ANCHOR`, `EVOLVE`, `AUDIT`, `STRIP`.

## Design Principles

G1 is built on several architectural assumptions:

- Data movement is more expensive than local computation  
- Execution state should remain causally traceable  
- Memory and compute should not exist as isolated subsystems  
- Parallel and scalar execution should share a unified logic substrate  

The architecture therefore prioritizes **locality**, **state stability**, and **execution transparency** over traditional pipeline-centric throughput scaling.

## Repository Status

G1 is currently an experimental research architecture and reference specification.

**This repository contains:**  
- Formal protocol definitions  
- Hardware interface specifications  
- SPL-Core execution semantics  
- Verification primitives for State Anchor integrity  

**Production silicon implementation is not currently available.**

## Performance Benchmarks (Theoretical)

| Metric | SPL-G1 | NVIDIA H200 | Advantage |
|--------|--------|-------------|-----------|
| Internal fabric bandwidth | ~128 TB/s | 4.8 TB/s (HBM3e) | **~27×** |
| Execution latency | 5–10 cycles | 400–600 cycles | **~60× faster** |
| Energy efficiency (equivalent inference workload) | Baseline | 17× higher consumption | **~17× more efficient** |
| Estimated TDP | 30–50W | 700W | **~15–23× lower power** |

A single G1-class processor is projected to deliver inference capability comparable to an entire rack of conventional GPUs while operating within a standard laptop power envelope.

---

*The narrative-driven computing era has ended. G1 is what comes next.*