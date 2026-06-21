"""
SP-EDA: 跨材料通用因果编译器内核 (完整增强版)
Version: 0.3.6
修复版本：修复10个安全/逻辑漏洞，包含路径遍历防护、线程安全、循环依赖检测等
"""

import re
import json
import os
import threading
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Set, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
import copy
import itertools
from collections import deque


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
# 新增反向映射
REVERSE_OP_MAPPING = {v: k for k, v in OP_MAPPING.items()}

@dataclass
class CausalOp:
    op_type: CausalOpType
    inputs: List[str]
    outputs: List[str]
    params: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        # 转义特殊字符，防止日志注入
        def escape(s):
            return s.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")
        escaped_ins = [escape(inp) for inp in self.inputs]
        escaped_outs = [escape(out) for out in self.outputs]
        return f"CausalOp({self.op_type.value.upper()}, ins={escaped_ins}, outs={escaped_outs})"


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
        
        # 新增：循环依赖检测（拓扑排序）
        in_degree = {op: len(op.inputs) for op in self.ops}
        queue = deque([op for op in self.ops if in_degree[op] == 0])
        processed = 0
        
        while queue:
            op = queue.popleft()
            processed += 1
            for out in op.outputs:
                for next_op in self.dataflow.get(out, []):
                    in_degree[next_op] -= 1
                    if in_degree[next_op] == 0:
                        queue.append(next_op)
        
        if processed != len(self.ops):
            raise ValueError("[IR自检失败] 数据流存在循环依赖")
        
        return True

    def clone(self) -> 'CausalIR':
        # 待优化：未来实现增量克隆提升性能，当前保持兼容
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
    
    def __post_init__(self):
        # 参数边界校验
        if self.max_delay_ns < 0 or self.max_delay_ns > 1e6:
            raise ValueError(f"max_delay_ns必须在0~1e6范围内，当前值：{self.max_delay_ns}")
        if self.max_power_mw < 0 or self.max_power_mw > 1e6:
            raise ValueError(f"max_power_mw必须在0~1e6范围内，当前值：{self.max_power_mw}")
        if self.max_area_um2 < 0 or self.max_area_um2 > 1e12:
            raise ValueError(f"max_area_um2必须在0~1e12范围内，当前值：{self.max_area_um2}")
        if self.min_snr_db < -100 or self.min_snr_db > 100:
            raise ValueError(f"min_snr_db必须在-100~100范围内，当前值：{self.min_snr_db}")

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
    
    def __post_init__(self):
        # 参数边界校验
        if self.delay_ns < 0 or self.delay_ns > 1e6:
            raise ValueError(f"delay_ns必须在0~1e6范围内，当前值：{self.delay_ns}")
        if self.power_mw < 0 or self.power_mw > 1e6:
            raise ValueError(f"power_mw必须在0~1e6范围内，当前值：{self.power_mw}")
        if self.area_um2 < 0 or self.area_um2 > 1e12:
            raise ValueError(f"area_um2必须在0~1e12范围内，当前值：{self.area_um2}")
        if self.snr_db < -100 or self.snr_db > 100:
            raise ValueError(f"snr_db必须在-100~100范围内，当前值：{self.snr_db}")


class MaterialLibrary:
    """材料工艺库：维护和导入不同物理媒介下的算子硬件参数"""
    # 存储结构统一修改为元组键，防止混淆：(material, op_type) -> List[ImplementationVariant]
    _variants: Dict[Tuple[str, CausalOpType], List[ImplementationVariant]] = {}
    _lock = threading.Lock()  # 新增：线程锁，解决竞态条件
    # 新增：PDK文件允许加载的目录白名单
    _allowed_pdk_dir = os.path.abspath("./pdk")

    @classmethod
    def register_variant(cls, variant: ImplementationVariant):
        with cls._lock:  # 加锁保护
            key = (variant.material, variant.op_type)
            cls._variants.setdefault(key, []).append(variant)

    @classmethod
    def get_variants(cls, material: str, op_type: CausalOpType) -> List[ImplementationVariant]:
        with cls._lock:  # 加锁保护
            variants = cls._variants.get((material, op_type), [])
            if not variants:
                raise ValueError(f"未找到材料{material}下算子{op_type}的实现变体")
            return variants

    @classmethod
    def clear_library(cls):
        """清空当前的工艺库缓存"""
        with cls._lock:  # 加锁保护
            cls._variants.clear()

    @classmethod
    def set_allowed_pdk_dir(cls, dir_path: str) -> None:
        """设置允许加载PDK文件的目录"""
        cls._allowed_pdk_dir = os.path.abspath(dir_path)

    @classmethod
    def load_from_pdk_file(cls, file_path: str) -> None:
        """
        核心新增函数：动态加载外部 PDK/工艺库 描述文件 (JSON 格式)
        支持通过配置直接切换材料底层，无需改动编译器内核
        """
        # 新增：路径安全校验，防止路径遍历漏洞
        abs_path = os.path.abspath(file_path)
        if not abs_path.startswith(cls._allowed_pdk_dir):
            raise PermissionError(f"[安全拦截] 非法PDK路径：{file_path}，仅允许加载{cls._allowed_pdk_dir}目录下的文件")
        
        # 修复：只捕获特定异常，不捕获系统级异常
        try:
            with open(abs_path, 'r', encoding='utf-8') as f:
                pdk_data = json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            raise IOError(f"[工艺导入失败] 无法读取或解析外部描述文件 {file_path}: {e}")

        material_name = pdk_data.get("material", "generic")
        cells = pdk_data.get("cells", {})

        for op_str, variants in cells.items():
            op_key = op_str.upper()
            
            if op_key not in OP_MAPPING:
                continue
            
            op_type = OP_MAPPING[op_key]
            for v in variants:
                # 参数提取和校验
                try:
                    delay_ns = float(v.get("delay_ns", 0.0))
                    power_mw = float(v.get("power_mw", 0.0))
                    area_um2 = float(v.get("area_um2", 0.0))
                    snr_db = float(v.get("snr_db", 30.0))
                except (ValueError, TypeError) as e:
                    raise ValueError(f"[工艺导入失败] 算子{op_str}参数类型错误：{e}")
                
                variant_obj = ImplementationVariant(
                    op_type=op_type,
                    material=material_name,
                    delay_ns=delay_ns,
                    power_mw=power_mw,
                    area_um2=area_um2,
                    snr_db=snr_db,
                    implementation_spec=v.get("implementation_spec", {})
                )
                cls.register_variant(variant_obj)
