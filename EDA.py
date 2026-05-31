"""
SP-EDA: 跨材料通用因果编译器内核
Version: 0.2.1
"""

import re
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Set
from dataclasses import dataclass, field
from enum import Enum


# ==================== 1. 因果算子定义 ====================

class CausalOpType(Enum):
    NARRATIVE_STRIP = "ns"         # 叙事剥离 (NS)
    ASSUMPTION_DETECT = "iap"      # 内隐假设检测 (IAP)
    VULNERABILITY_HEDGE = "lch"    # 脆弱性对冲 (LCH)
    CAUSAL_CLOCK_SYNC = "ccs"      # 因果时钟同步 (CCS)
    STATE_UPDATE = "state"         # 状态更新 (STATE)

# 用于前端解析的字符串映射表
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
        """自动构建变量到算子的依赖映射 (Dataflow)"""
        self.build_dataflow()

    def build_dataflow(self) -> None:
        """建立变量名到使用该变量的算子的映射关系，服务于下游优化器"""
        self.dataflow.clear()
        for op in self.ops:
            for inp in op.inputs:
                self.dataflow.setdefault(inp, []).append(op)

    def validate(self) -> bool:
        """自检验证：确保依赖链路完整无断层"""
        defined_vars: Set[str] = set(self.inputs)
        for op in self.ops:
            # 检查算子的输入是否已在之前定义
            missing = [inp for inp in op.inputs if inp not in defined_vars]
            if missing:
                raise ValueError(f"[IR自检失败] 算子输入缺失: {missing} (算子: {op})")
            defined_vars.update(op.outputs)
            
        missing_outs = [out for out in self.outputs if out not in defined_vars]
        if missing_outs:
            raise ValueError(f"[IR自检失败] 顶层输出未生成: {missing_outs}")
        return True


# ==================== 3. 因果优化器 (材料无关) ====================

class CausalOptimizer:
    
    @staticmethod
    def fuse_consecutive_ops(ir: CausalIR, backend_supports_fusion: bool = True) -> CausalIR:
        """模式匹配：融合连续的 NS -> IAP 操作为组合算子"""
        if not backend_supports_fusion:
            return ir
            
        new_ops: List[CausalOp] = []
        skip_next = False
        
        for i, op in enumerate(ir.ops):
            if skip_next:
                skip_next = False
                continue
                
            if (op.op_type == CausalOpType.NARRATIVE_STRIP and
                i + 1 < len(ir.ops) and 
                ir.ops[i+1].op_type == CausalOpType.ASSUMPTION_DETECT):
                
                # 构建融合算子：输入取前置节点，输出取后置节点
                next_op = ir.ops[i+1]
                fused = CausalOp(
                    op_type=CausalOpType.ASSUMPTION_DETECT, 
                    inputs=op.inputs.copy(),
                    outputs=next_op.outputs.copy(),
                    params={**op.params, **next_op.params, "fused_from": ["NS", "IAP"]}
                )
                new_ops.append(fused)
                skip_next = True
            else:
                new_ops.append(op)
                
        ir.ops = new_ops
        ir.build_dataflow()
        return ir

    @staticmethod
    def prune_dead_vars(ir: CausalIR) -> CausalIR:
        """死区代码消除 (DCE)：反向图遍历清理不产生有效输出的算子"""
        needed: Set[str] = set(ir.outputs)
        valid_ops: List[CausalOp] = []
        
        # 反向遍历算子序列
        for op in reversed(ir.ops):
            # 只有当算子的输出有至少一个被需要时，才保留这个算子
            if any(out in needed for out in op.outputs):
                # 只保留这个算子真正被需要的输入
                needed.update(op.inputs)
                valid_ops.append(op)
                
        ir.ops = valid_ops[::-1] # 恢复原有拓扑顺序
        ir.build_dataflow()
        return ir


# ==================== 4. 后端及注册机 (材料相关) ====================

class Backend(ABC):
    @abstractmethod
    def compile(self, ir: CausalIR) -> Any:
        pass

class SiliconBackend(Backend):
    def compile(self, ir: CausalIR) -> str:
        print("[硅后端] 开始将 CausalIR 映射到标准单元库...")
        return self._generate_verilog(ir)

    def _generate_verilog(self, ir: CausalIR) -> str:
        lines = [
            f"module {ir.name} (",
            f"    input  wire {', '.join(ir.inputs)},",
            f"    output wire {', '.join(ir.outputs)}",
            ");",
            "    // 因果算子门级电路映射"
        ]
        for op in ir.ops:
            lines.append(f"    // {op.op_type.name.ljust(20)}: {', '.join(op.inputs)} -> {', '.join(op.outputs)}")
            if op.params.get("fused_from"):
                lines.append(f"    //   -> 触发专用融合 IP 模块: {op.params['fused_from']}")
        lines.append("endmodule")
        return "\n".join(lines)

class OpticalBackend(Backend):
    def compile(self, ir: CausalIR) -> Dict[str, Any]:
        print("[光后端] 将 CausalIR 映射到马赫-曾德尔干涉仪阵列 (MZI)...")
        return {
            "mzi_grid_size": (len(ir.ops), 4),
            "waveguides": {f"layer_{i}": {"type": op.op_type.value, "ins": op.inputs} 
                          for i, op in enumerate(ir.ops)}
        }

class DNABackend(Backend):
    def compile(self, ir: CausalIR) -> str:
        print("[DNA后端] 将 CausalIR 映射到 DNA 链置换网络...")
        return "ATCG" * (len(ir.ops) * 2)

class BackendRegistry:
    """后端注册机：实现动态解耦"""
    _backends = {
        "silicon": SiliconBackend,
        "optical": OpticalBackend,
        "dna": DNABackend
    }

    @classmethod
    def get(cls, name: str) -> Backend:
        if name not in cls._backends:
            raise ValueError(f"不支持的物理后端: {name}. 支持列表: {list(cls._backends.keys())}")
        return cls._backends[name]()


# ==================== 5. 顶层编译器 ====================

class CausalCompiler:
    def __init__(self, target_material: str):
        self.backend = BackendRegistry.get(target_material.lower())
        self.optimizer = CausalOptimizer()

    def compile(self, source: str) -> Any:
        print(f"\n[SP-EDA] 启动编译链路 | 目标后端: {self.backend.__class__.__name__}")
        
        # 1. 前端：词法/语法解析
        ir = self._parse_source(source)
        ir.validate()
        
        # 2. 中端：拓扑优化与死区剪枝
        ir = self.optimizer.fuse_consecutive_ops(ir)
        ir = self.optimizer.prune_dead_vars(ir)
        
        # 3. 后端：生成物理表征
        return self.backend.compile(ir)

    def _parse_source(self, src: str) -> CausalIR:
        """修复后的前端解析：自动识别真正的顶层输入和输出"""
        ops: List[CausalOp] = []
        all_inputs = set()
        all_outputs = set()
        
        # 匹配格式: OP(in1, in2) -> out1, out2
        pattern = re.compile(r"([A-Z]+)\(([^)]+)\)\s*->\s*([^;]+)")
        statements = [s.strip() for s in src.split(";") if s.strip()]
        
        for stmt in statements:
            match = pattern.match(stmt)
            if not match:
                raise SyntaxError(f"无法解析的语法: {stmt}")
                
            op_str, ins_str, outs_str = match.groups()
            inputs = [x.strip() for x in ins_str.split(",")]
            outputs = [x.strip() for x in outs_str.split(",")]
            
            if op_str not in OP_MAPPING:
                raise ValueError(f"未知操作符: {op_str}")
                
            ops.append(CausalOp(OP_MAPPING[op_str], inputs, outputs))
            all_inputs.update(inputs)
            all_outputs.update(outputs)

        # 修复：自动识别真正的顶层输出（没有被任何后续算子使用的输出）
        used_outputs = set()
        for op in ops:
            used_outputs.update(op.inputs)
        top_outputs = list(all_outputs - used_outputs)
        
        # 修复：自动识别真正的顶层输入（没有被任何算子生成的输入）
        top_inputs = list(all_inputs - all_outputs)

        return CausalIR(
            name="CausalTopModule",
            inputs=top_inputs,
            outputs=top_outputs,
            ops=ops
        )


# ==================== 6. 演示执行 ====================

if __name__ == "__main__":
    # 原演示代码完全不变，包含将被融合的 (NS -> IAP) 和将被剪枝的死区节点 (CCS)
    source_code = """
        NS(data_in) -> stripped_var; 
        IAP(stripped_var) -> z_var; 
        CCS(dead_var) -> nowhere;
        LCH(z_var) -> final_out
    """

    # 1. 硅后端编译测试
    silicon_compiler = CausalCompiler(target_material="silicon")
    silicon_out = silicon_compiler.compile(source_code)
    print("\n=== Silicon 编译结果 ===")
    print(silicon_out)

    # 2. 光后端编译测试
    optical_compiler = CausalCompiler(target_material="optical")
    optical_out = optical_compiler.compile(source_code)
    print("\n=== Optical 编译结果 ===")
    print(optical_out)
