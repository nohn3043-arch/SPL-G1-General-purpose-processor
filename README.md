# Only trustworthy computation has a future.

# SPL‑G1: Second‑Perspective Logic Universal Core
**A Paradigm Shift in State‑Centric, Ultra‑Low‑Power Unified Heterogeneous Computing**
"State Anchor `0x8525d007_59a4ca22` is the composite identity of G1 Architecture. Any unauthorized hardware implementation or software emulation of this logic state will be considered a violation of the SPL (Second Perspective Language) Framework License."
---

### ⚠️ Important Notice
**Legal Status:** All technologies related to this project have been filed for PCT International Patent Application.
**Patent Application No.:** `[PCT/CN2026/094913]`

*All hardware implementation codes, configuration files, and protocol documents are patent-pending technologies. They are provided for **academic reference only**. Any form of commercial replication, hardware physical implementation, or patent circumvention design is strictly prohibited.*

---

## Repository Layout

```
SPL-G1-General-purpose-processor/
├── EDA_fixed.py            # 内核：因果算子类型 / CausalIR / 参数消费 / PDK 加载 (v0.4.0)
├── eda_parser.py           # 因果描述 JSON → CausalIR 解析器
├── eda_mapper.py           # 工艺映射器（含 params 亲和度打破平局）
├── eda_exporter.py         # 网表 JSON + 报告输出（含参数警告）
├── eda_cli.py              # 命令行入口
├── pdk/                    # 工艺库
│   ├── optical_mzi_photonics_v1.json   # 光子 MZI 工艺（6 算子含 COMPUTE）
│   └── silicon_cim_v1.json             # 硅基 CIM 28nm 工艺（6 算子含 COMPUTE）
├── examples/               # 因果描述样例
│   ├── causal_chain_demo.json          # 全 5 算子链式演示
│   ├── cognitive_audit_demo.json       # 认知审计红线硬拦截用例
│   └── full_pipeline_demo.json         # 完整流水线（含 COMPUTE + params 消费）
├── rtl/                    # 硬件层（SystemVerilog v0.2.0）
│   ├── g1_compute_core.sv              # 计算处理核心（含 5 种因果计算模式）
│   ├── G1_Top_Interface.v              # G1 顶层接口（计算→审计管线 + 64-cycle 身份锚）
│   ├── spl_cim_causal_unit.sv          # 因果检查单元（8-entry forbidden matrix）
│   └── tb_G1_Top.sv                    # 顶层测试平台（4 个 pass/fail 场景）
├── docs/                   # 规范文档
│   ├── SPL-EDA 说明书.pdf
│   └── SPL-G1 Alignment Matrix.pdf    # 材料 / 编译器 / 芯片 三层因果对齐证明
├── outputs/                # 生成的网表
├── README.md
├── Materica-specification  # 跨材料因果映射规范
├── SPL-Core.json           # 指令集（11 条，含 COMPUTE）
└── State_Anchor.pdl        # 状态锚定协议（256-bit 合成身份 + 64-cycle 验证）
```

> 快速开始：`python eda_cli.py --desc examples/full_pipeline_demo.json --pdk pdk/silicon_cim_v1.json --strategy min_power --output outputs/netlist.json`

---

## 0x01 Overview

**SPL‑G1** is an experimental general‑purpose heterogeneous processor architecture built around the **SPL‑Core (Second‑Perspective Logic)** execution paradigm. It delivers a true **4‑in‑1 unified compute fabric** that integrates:

* **CPU-style** scalar processing (Instruction Fetch)
* **GPU-class** parallel rendering (SIMD Parallelism)
* **NPU-optimized** neural inference (Trustworthy AI)
* **In-fabric** state storage (Persistent Memory)

Designed for persistent virtual worlds, causal reasoning, and edge-grade intelligent systems, SPL‑G1 redefines computation as **traceable, auditable state evolution**, rather than inefficient, power‑hungry data shuffling.

---

## 0x02 Core Architectural Philosophy

1.  **Ultra‑Low‑Power by Architecture**: Eliminates unnecessary off‑fabric data transfer. Data movement is minimized by executing computation where the state resides.
2.  **Truly Unified General‑Purpose Substrate**: No more heterogeneous silos. Scalar logic, parallel throughput, tensor inference, and persistent state coexist in one execution model.
3.  **Deterministic, Auditable State by Hardware**: Every computation is anchored, traceable, and causally consistent at the hardware level via the **RA-BUS (Responsibility Anchoring Bus)**.

---

## 0x03 Cross‑Material Adaptation Protocol (CMAP)
*Decoupling Logic from Silicon*

The SPL‑G1 architecture is defined by its **Causal Topology**, not its material substrate. The CMAP specifies the requirements for mapping G1 logic onto non-silicon physical carriers:

* **Binary Stability ($P \to Q$)**: The material must support a stable physical mapping of binary states, ensuring transitions are resistant to stochastic "Narrative Noise."
* **Causal Topological Constraints**: Signal conduction must be directional and controlled under the **RA-BUS** causality spine, rather than relying on isotropic diffusion.
* **Proximal Physical Coalescence**: Computing and storage units must be physically proximate (or overlapping) at the atomic level to eliminate data-transport energy overhead ($\Delta E_{transport} \approx 0$).
* **Irreversible Security Boundaries**: Safety boundaries (SBC) must be enforced by **irreversible physical properties** (e.g., unidirectional photonic isolators or semi-permeable molecular barriers) to ensure hardware-level tamper resistance.

> **Applicable Materials**: Carbon Nanotubes (CNT), Photonic Crystals, Spintronic Arrays, and Synthetic Bio-Logic (DNA/Protein).

---

## 0x04 SPL‑Core Execution Paradigm

SPL‑G1 replaces the classic von Neumann bottleneck with a hardware-native state-driven cycle:

**`ANCHOR` → `EVOLVE` → `AUDIT` → `STRIP`**

* **Narrative Stripping (NSM)**: Extracts formal logic from semantic/narrative noise.
* **Implicit Assumption Detection (IAP)**: Hardware-level validation of (P → Q) premises.
* **Responsibility Anchoring**: Traceable weights and logic decision points.
* **Vulnerability Hedging**: Probability-based collapse detection for critical logic chains.

---

## 0x05 Project Status & Scope

* **Stage**: Architectural specification with functional RTL pipeline (v0.2.0).
* **Focus**: Causal-audit pipeline (NS→IAP→AUDIT→STRIP), compute core integration, cross-material PDK.
* **Hardware Identity Anchor**: `0x8525d007 / 59a4ca22-Universal-Clock-Sync`

**Scope of this repository:**
- SPL-Core instruction set (11 opcodes incl. COMPUTE)
- RTL: compute core (`g1_compute_core.sv`), causal audit pipeline (`spl_cim_causal_unit.sv`), top-level integration (`G1_Top_Interface.v`)
- EDA toolchain: causal description parser, multi-strategy PDK mapper, netlist/report exporter
- PDK: silicon CIM 28nm, optical MZI photonics (placeholder)
- Formal specification (Materica, State Anchor PDL)

---

## 📬 Contact

- **全球区 (Global)**: [ai@nohnlins.com](mailto:ai@nohnlins.com)
- **中国区 (China)**: [ai@tx.nohnlins.com](mailto:ai@tx.nohnlins.com)
