"""
SP-EDA: 跨材料通用因果编译器内核 (完整增强版)
Version: 0.3.0
新增模块：物理抽象层(PAL)、自动探索器、等价性检查器
"""

import re
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Set, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
import copy
import itertools


# ==================== 1. 因果算子定义 ====================

class CausalOpType(Enum):
    NARRATIVE_STRIP = "ns"         # 叙事剥离 (NS)
    ASSUMPTION_DETECT = "iap"      # 内隐假设检测 (IAP)
    VULNERABILITY_HEDGE = "lch"    # 脆弱性对冲 (LCH)
    CAUSAL_CLOCK_SYNC = "ccs"      # 因果时钟同步 (CCS)
    STATE_UPDATE = "state"         # 状态更新 (STATE)

OP_MAPPING = {
    "NS": CausalOpType.NARRATIVE_STRIP,
    "IAP": CausalOpType.ASSUMPTION_DETECT,
    "LCH": CausalOpType.VULNERABILITY_HEDGE,
    "CCS": CausalOpType.CAUSAL_CLOCK_SYNC,
    "STATE": CausalOpType.STATE_UPDATE
}

@dataclass
class CausalOp:
    op_type: CausalOpType
    inputs: List[str]
    outputs: List[str]
    params: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"CausalOp({self.op_type.value.upper()}, ins={self.inputs}, outs={self.outputs})"


# ==================== 2. 因果中间表示 (Causal IR) ====================

@dataclass
class CausalIR:
    name: str
    inputs: List[str]
    outputs: List[str]
    ops: List[CausalOp]
    dataflow: Dict[str, List[CausalOp]] = field(default_factory=dict)

    def __post_init__(self):
        self.build_dataflow()

    def build_dataflow(self) -> None:
        self.dataflow.clear()
        for op in self.ops:
            for inp in op.inputs:
                self.dataflow.setdefault(inp, []).append(op)

    def validate(self) -> bool:
        defined_vars: Set[str] = set(self.inputs)
        for op in self.ops:
            missing = [inp for inp in op.inputs if inp not in defined_vars]
            if missing:
                raise ValueError(f"[IR自检失败] 算子输入缺失: {missing} (算子: {op})")
            defined_vars.update(op.outputs)
        missing_outs = [out for out in self.outputs if out not in defined_vars]
        if missing_outs:
            raise ValueError(f"[IR自检失败] 顶层输出未生成: {missing_outs}")
        return True

    def clone(self) -> 'CausalIR':
        """深拷贝一份IR"""
        return copy.deepcopy(self)


# ==================== 3. 物理抽象层 (PAL) ====================

@dataclass
class PhysicalConstraints:
    """材料物理约束描述"""
    material: str
    # 通用约束
    max_delay_ns: float = 10.0          # 最大允许延迟 (ns)
    max_power_mw: float = 100.0         # 最大功耗 (mW)
    max_area_um2: float = 1e6           # 最大面积 (um^2)
    min_snr_db: float = 20.0            # 最小信噪比 (dB)
    # 材料特有参数 (示例)
    extra: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ImplementationVariant:
    """某个算子在特定材料下的实现变体"""
    op_type: CausalOpType
    material: str
    # 物理特性
    delay_ns: float
    power_mw: float
    area_um2: float
    snr_db: float
    # 实现描述 (例如Verilog片段、MZI配置等)
    implementation_spec: Dict[str, Any] = field(default_factory=dict)

class MaterialLibrary:
    """材料库：存储每种材料下各算子的可选实现变体"""
    _variants: Dict[str, List[ImplementationVariant]] = {}  # key: (material, op_type)

    @classmethod
    def register_variant(cls, variant: ImplementationVariant):
        key = (variant.material, variant.op_type)
        cls._variants.setdefault(key, []).append(variant)

    @classmethod
    def get_variants(cls, material: str, op_type: CausalOpType) -> List[ImplementationVariant]:
        return cls._variants.get((material, op_type), [])

    @classmethod
    def load_default_library(cls):
        """加载默认的一些实现变体（示例数据）"""
        # 硅材料下各种算子的实现
        variants_silicon = [
            ImplementationVariant(CausalOpType.NARRATIVE_STRIP, "silicon",
                                  delay_ns=1.2, power_mw=5.0, area_um2=100,
                                  implementation_spec={"type": "asic", "cells": ["AND", "OR"]}),
            ImplementationVariant(CausalOpType.NARRATIVE_STRIP, "silicon",
                                  delay_ns=0.8, power_mw=8.0, area_um2=120,
                                  implementation_spec={"type": "asic", "cells": ["NAND", "NOR"]}),
            ImplementationVariant(CausalOpType.ASSUMPTION_DETECT, "silicon",
                                  delay_ns=2.0, power_mw=10.0, area_um2=200,
                                  implementation_spec={"type": "asic", "cells": ["XOR", "MUX"]}),
            ImplementationVariant(CausalOpType.VULNERABILITY_HEDGE, "silicon",
                                  delay_ns=1.5, power_mw=6.0, area_um2=150,
                                  implementation_spec={"type": "asic", "cells": ["ADD", "COMP"]}),
            ImplementationVariant(CausalOpType.CAUSAL_CLOCK_SYNC, "silicon",
                                  delay_ns=0.5, power_mw=3.0, area_um2=80,
                                  implementation_spec={"type": "asic", "cells": ["DFF"]}),
        ]
        # 光学材料
        variants_optical = [
            ImplementationVariant(CausalOpType.NARRATIVE_STRIP, "optical",
             