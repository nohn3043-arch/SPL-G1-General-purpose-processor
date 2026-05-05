// 
module G1_Top_Interface_Complete (
    input wire clk,
    input wire rst_n,
    inout wire [511:0] ra_bus_data,   // 总线上的大数据
    input wire [63:0]  ra_bus_addr,   // 决定发给哪个单元的“门牌号”
    input wire         ra_bus_valid
    // ... 其他接口省略
);

    // 1. 分发逻辑：根据地址(addr)生成选通信号
    wire [3:0] unit_sel; // 假设我们有4个计算单元
    assign unit_sel[0] = (ra_bus_addr[1:0] == 2'b00) && ra_bus_valid;
    assign unit_sel[1] = (ra_bus_addr[1:0] == 2'b01) && ra_bus_valid;
    assign unit_sel[2] = (ra_bus_addr[1:0] == 2'b10) && ra_bus_valid;
    assign unit_sel[3] = (ra_bus_addr[1:0] == 2'b11) && ra_bus_valid;

    // 2. 实例化：把你的“大脑细胞”成排地焊上去
    // 这里用到了你之前写的 spl_cim_causal_unit
    generate
        genvar i;
        for (i=0; i<4; i=i+1) begin : causal_array
            spl_cim_causal_unit u_unit (
                .clk(clk),
                .rst_n(rst_n),
                .wr_en(unit_sel[i]),           // 只有选中的单元才干活
                .wr_data_p(ra_bus_data[255:0]), // 共享数据总线
                .wr_data_q(ra_bus_data[511:256]),
                // ... 其他信号
                .logic_valid(unit_valids[i])
            );
        end
    endgenerate

endmodule
