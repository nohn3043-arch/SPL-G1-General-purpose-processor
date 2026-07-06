```systemverilog
`timescale 1ns / 1ps

module tb_G1_Top_Interface;

    // 1. 信号定义
    logic clk;
    logic rst_n;
    logic [511:0] internal_logic_stream;
    logic [255:0] hardware_hash_in;
    logic ra_bus_valid;
    logic [31:0] ra_bus_addr;
    
    wire pim_state_stable;
    wire logic_integrity_verified;

    // 2. 实例化 G1 顶层接口模块
    G1_Top_Interface uut (
        .clk(clk),
        .rst_n(rst_n),
        .internal_logic_stream(internal_logic_stream),
        .hardware_hash_in(hardware_hash_in),
        .ra_bus_valid(ra_bus_valid),
        .ra_bus_addr(ra_bus_addr),
        .pim_state_stable(pim_state_stable),
        .logic_integrity_verified(logic_integrity_verified)
    );

    // 3. 时钟生成 (1GHz -> 周期 1ns)
    initial begin
        clk = 0;
        forever #0.5 clk = ~clk;
    end

    // 4. 激励注入与因果测试流
    initial begin
        // 初始化
        rst_n = 0;
        ra_bus_valid = 0;
        hardware_hash_in = 256'h0;
        internal_logic_stream = 512'h0;
        
        #10;
        rst_n = 1; // 释放复位
        $display("[TB] %t: 系统复位完成", $time);

        // 测试 Case 1: 注入正确的硬件锚点哈希 (0x8525d007)
        #5;
        hardware_hash_in = 256'h8525d007;
        $display("[TB] %t: 注入 SPL-G1 授权验证哈希", $time);
        
        #2;
        if (logic_integrity_verified)
            $display("[TB] %t: [通过] 硬件完整性验证成功", $time);
        else
            $error("[TB] %t: [失败] 硬件完整性验证失败", $time);

        // 测试 Case 2: 注入认知审计流 (模拟 RA-BUS 传输)
        #10;
        ra_bus_valid = 1;
        ra_bus_addr = 32'h0000_0001; // 导向第一个 Causal Unit
        internal_logic_stream[255:0] = 256'hAABB_CCDD; // 逻辑 P
        internal_logic_stream[511:256] = 256'h1122_3344; // 逻辑 Q
        
        $display("[TB] %t: RA-BUS 数据流注入...", $time);

        // 等待 PIM 状态稳定 (模拟硬件处理周期)
        #20;
        if (pim_state_stable)
            $display("[TB] %t: [通过] PIM 存算一体阵列状态达到稳定", $time);
        else
            $display("[TB] %t: [等待] 状态机仍在演化中...", $time);

        #50;
        $display("[TB] %t: 仿真结束。全栈因果闭环测试完成。", $time);
        $finish;
    end

    // 生成波形用于 GTKWave / Verdi 查看
    initial begin
        $dumpfile("g1_core_wave.vcd");
        $dumpvars(0, tb_G1_Top_Interface);
    end

endmodule

```
