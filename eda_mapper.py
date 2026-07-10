"""
SP-EDA 工艺映射器 (v0.1.0)

遍历 CausalIR 中的每个因果算子，从 MaterialLibrary 匹配物理实现变体，
按物理约束筛选，按策略选择最优变体。

支持映射策略:
- "first_fit": 选择第一个满足所有约束的变体
- "min_delay": 在满足约束的变体中选延迟最低的
- "min_power": 在满足约束的变体中选功耗最低的
- "min_area":  在满足约束的变体中选面积最小的
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum

from EDA_fixed import (
    CausalIR, CausalOp, CausalOpType,
    PhysicalConstraints, ImplementationVariant,
    MaterialLibrary, REVERSE_OP_MAPPING,
    validate_op_params, params_affinity_score   # v0.4.0
)


class MappingStrategy(Enum):
    FIRST_FIT = "first_fit"
    MIN_DELAY = "min_delay"
    MIN_POWER = "min_power"
    MIN_AREA = "min_area"


@dataclass
class OpMapping:
    """单个算子的映射结果"""
    op_index: int
    op_type: str
    inputs: List[str]
    outputs: List[str]
    selected: Optional[ImplementationVariant] = None
    alternatives: List[ImplementationVariant] = field(default_factory=list)
    all_candidates: List[ImplementationVariant] = field(default_factory=list)
    failed_reason: Optional[str] = None          # 无满足约束的变体时记录原因
    param_warnings: List[str] = field(default_factory=list)  # v0.4.0


@dataclass
class MappingResult:
    """完整映射结果"""
    design_name: str
    material: str
    strategy: str
    constraints: PhysicalConstraints
    ops: List[OpMapping]
    total_delay_ns: float = 0.0
    total_power_mw: float = 0.0
    total_area_um2: float = 0.0
    min_snr_db: float = 0.0
    all_passed: bool = True
    unmapped_count: int = 0

    def summary_text(self) -> str:
        status = "OK" if self.all_passed else f"FAILED ({self.unmapped_count} 个算子未映射)"
        return (
            f"映射结果 [{status}]\n"
            f"  设计: {self.design_name}\n"
            f"  材料: {self.material}\n"
            f"  策略: {self.strategy}\n"
            f"  约束: delay<={self.constraints.max_delay_ns}ns "
            f"power<={self.constraints.max_power_mw}mW "
            f"area<={self.constraints.max_area_um2}um2 "
            f"snr>={self.constraints.min_snr_db}dB\n"
            f"  合计: delay={self.total_delay_ns:.1f}ns "
            f"power={self.total_power_mw:.1f}mW "
            f"area={self.total_area_um2:.1f}um2 "
            f"min_snr={self.min_snr_db:.1f}dB\n"
            f"  算子: {len(self.ops)} 总 / {self.unmapped_count} 未映射"
        )


def _variant_passes(variant: ImplementationVariant,
                    constraints: PhysicalConstraints) -> Tuple[bool, str]:
    """检查单个变体是否满足物理约束。返回 (通过, 失败原因)。"""
    if variant.delay_ns > constraints.max_delay_ns:
        return False, (
            f"delay {variant.delay_ns}ns > max {constraints.max_delay_ns}ns"
        )
    if variant.power_mw > constraints.max_power_mw:
        return False, (
            f"power {variant.power_mw}mW > max {constraints.max_power_mw}mW"
        )
    if variant.area_um2 > constraints.max_area_um2:
        return False, (
            f"area {variant.area_um2}um2 > max {constraints.max_area_um2}um2"
        )
    if variant.snr_db < constraints.min_snr_db:
        return False, (
            f"snr {variant.snr_db}dB < min {constraints.min_snr_db}dB"
        )
    return True, ""


def _select_variant(passing: List[ImplementationVariant],
                    strategy: MappingStrategy,
                    op: CausalOp = None) -> ImplementationVariant:
    """从满足约束的变体列表中按策略选择一个。
    如果只有一个变体，直接返回。
    如果有多个，用算子 params 的亲和度打分打破平局 (v0.4.0)。
    """
    if len(passing) == 1:
        return passing[0]

    # 主策略排序
    if strategy == MappingStrategy.FIRST_FIT:
        primary = passing[0]
    elif strategy == MappingStrategy.MIN_DELAY:
        primary = min(passing, key=lambda v: v.delay_ns)
    elif strategy == MappingStrategy.MIN_POWER:
        primary = min(passing, key=lambda v: v.power_mw)
    elif strategy == MappingStrategy.MIN_AREA:
        primary = min(passing, key=lambda v: v.area_um2)
    else:
        primary = passing[0]

    # 亲和度决断：如果主策略最优值和第二名差距 < 5%，用 params 重排序
    if op is not None and len(passing) > 1:
        # 找到与 primary 在关键指标上差距 < 5% 的候选
        def is_close(variant):
            if strategy == MappingStrategy.MIN_DELAY:
                return variant.delay_ns <= primary.delay_ns * 1.05
            elif strategy == MappingStrategy.MIN_POWER:
                return variant.power_mw <= primary.power_mw * 1.05
            elif strategy == MappingStrategy.MIN_AREA:
                return variant.area_um2 <= primary.area_um2 * 1.05
            return False

        close_candidates = [v for v in passing if is_close(v) or v is primary]
        if len(close_candidates) > 1:
            # 按亲和度分从高到低排序，选最高的
            close_candidates.sort(key=lambda v: params_affinity_score(op, v), reverse=True)
            return close_candidates[0]

    return primary


def map_causal_ir(
    ir: CausalIR,
    material: str,
    constraints: PhysicalConstraints,
    strategy: MappingStrategy = MappingStrategy.MIN_DELAY
) -> MappingResult:
    """
    对 CausalIR 执行工艺映射。

    Args:
        ir: 因果中间表示
        material: 目标材料名称（如 "optical_mzi_photonics_v1"）
        constraints: 物理约束
        strategy: 映射策略

    Returns:
        MappingResult 包含每个算子的变体选择及汇总
    """
    op_mappings: List[OpMapping] = []
    total_delay = 0.0
    total_power = 0.0
    total_area = 0.0
    min_snr = float('inf')
    unmapped = 0

    for i, op in enumerate(ir.ops):
        op_code = REVERSE_OP_MAPPING.get(op.op_type, 'UNKNOWN')
        mapping = OpMapping(
            op_index=i,
            op_type=op_code,
            inputs=list(op.inputs),
            outputs=list(op.outputs)
        )

        # v0.4.0: 校验算子参数
        mapping.param_warnings = validate_op_params(op)

        # 获取该算子在该材料下的所有变体
        try:
            all_variants = MaterialLibrary.get_variants(material, op.op_type)
        except ValueError:
            mapping.failed_reason = f"材料 {material} 下无算子 {op_code} 的工艺变体"
            mapping.all_candidates = []
            unmapped += 1
            op_mappings.append(mapping)
            continue

        mapping.all_candidates = list(all_variants)

        # 按约束筛选
        passing = []
        for variant in all_variants:
            ok, reason = _variant_passes(variant, constraints)
            if ok:
                passing.append(variant)
            else:
                mapping.alternatives.append(variant)  # 保存未通过的作为备选参考

        if not passing:
            mapping.failed_reason = (
                f"共 {len(all_variants)} 个变体均不满足约束 "
                f"(delay<={constraints.max_delay_ns}, "
                f"power<={constraints.max_power_mw}, "
                f"area<={constraints.max_area_um2}, "
                f"snr>={constraints.min_snr_db})"
            )
            unmapped += 1
        else:
            selected = _select_variant(passing, strategy, op)
            mapping.selected = selected
            total_delay += selected.delay_ns
            total_power += selected.power_mw
            total_area += selected.area_um2
            min_snr = min(min_snr, selected.snr_db)

        op_mappings.append(mapping)

    return MappingResult(
        design_name=ir.name,
        material=material,
        strategy=strategy.value,
        constraints=constraints,
        ops=op_mappings,
        total_delay_ns=total_delay,
        total_power_mw=total_power,
        total_area_um2=total_area,
        min_snr_db=min_snr if min_snr != float('inf') else 0.0,
        all_passed=(unmapped == 0),
        unmapped_count=unmapped
    )
