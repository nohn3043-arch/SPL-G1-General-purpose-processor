"""
SP-EDA: 跨材料通用因果编译器内核 (完整增强版)
Version: 0.3.5
新增功能：外挂工艺库描述文件(PDK)动态加载接口，彻底解耦物理参数与编译器内核
"""

import re
import json
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

# 支持前端算子缩写到内核枚举的双向映射
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
        return copy.deepcopy(self)


# ==================== 3. 物理抽象层 (PAL) 与物理工艺导入 ====================

@dataclass
class PhysicalConstraints:
    """材料物理约束描述"""
    material: str
    max_delay_ns: float = 10.0          # 最大允许延迟 (ns)
    max_power_mw: float = 100.0         # 最大功耗 (mW)
    max_area_um2: float = 1e6           # 最大面积 (um^2)
    min_snr_db: float = 20.0            # 最小信噪比 (dB)
    extra: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ImplementationVariant:
    """某个算子在特定材料下的物理实现变体"""
    op_type: CausalOpType
    material: str
    delay_ns: float
    power_mw: float
    area_um2: float
    snr_db: float
    implementation_spec: Dict[str, Any] = field(default_factory=dict)


class MaterialLibrary:
    """材料工艺库：维护和导入不同物理媒介下的算子硬件参数"""
    # 存储结构统一修改为元组键，防止混淆：(material, op_type) -> List[ImplementationVariant]
    _variants: Dict[Tuple[str, CausalOpType], List[ImplementationVariant]] = {}

    @classmethod
    def register_variant(cls, variant: ImplementationVariant):
        key = (variant.material, variant.op_type)
        cls._variants.setdefault(key, []).append(variant)

    @classmethod
    def get_variants(cls, material: str, op_type: CausalOpType) -> List[ImplementationVariant]:
        return cls._variants.get((material, op_type), [])

    @classmethod
    def clear_library(cls):
        """清空当前的工艺库缓存"""
        cls._variants.clear()

    @classmethod
    def load_from_pdk_file(cls, file_path: str) -> None:
        """
        核心新增函数：动态加载外部 PDK/工艺库 描述文件 (JSON 格式)
        支持通过配置直接切换材料底层，无需改动编译器内核
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                pdk_data = json.load(f)
        except Exception as e:
            raise IOError(f"[工艺导入失败] 无法读取或解析外部描述文件 {file_path}: {e}")

        material_name = pdk_data.get("material", "generic")
        cells = pdk_data.get("cells", {})

        for op_str, variants in cells.items():
            op_key = op_str.upper()
            
            if op_key not in OP_MAPPING:
                continue
            
            op_type = OP_MAPPING[op_key]
            for v in variants:
                variant_obj = ImplementationVariant(
                    op_type=op_type,
                    material=material_name,
                    delay_ns=float(v.get("delay_ns", 0.0)),
                    power_mw=float(v.get("power_mw", 0.0)),
                    area_um2=float(v.get("area_um2", 0.0)),
                    snr_db=float(v.get("snr_db", 30.0)), # 默认较高信噪比
                    implementation_spec=v.get("implementation_spec", {})
                )
                cls.register_variant(variant_obj)
