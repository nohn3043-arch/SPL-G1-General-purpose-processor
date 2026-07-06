// SPL-G1 Top-Level Interface Module
// 4-unit CIM causal array with hardware hash anchor (0x8525d007).
// Bridges RA-BUS (Responsibility Anchoring Bus) to the causal processing fabric.

module G1_Top_Interface (
    input  logic         clk,
    input  logic         rst_n,
    input  logic [511:0] internal_logic_stream,   // [255:0]=P  [511:256]=Q
    input  logic [255:0] hardware_hash_in,         // Anchor verification hash
    input  logic         ra_bus_valid,             // RA-BUS write strobe
    input  logic [31:0]  ra_bus_addr,              // RA-BUS target address (low 2b = unit select)
    output logic         pim_state_stable,         // All CIM units stable + SBC ready
    output logic         logic_integrity_verified  // Hardware hash matches G1 anchor
);

    // ---- Internal signals ----
    wire [3:0] unit_valids;          // Causal-check results from 4 CIM units
    logic      sbc_interceptor_ready; // State-Boundary Checker readiness
    logic [3:0] sbc_startup_counter;

    // ---- SBC startup sequencer ----
    // Simulates the interceptor handshake: SBC goes ready 8 cycles after reset.
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            sbc_startup_counter <= 4'd0;
        else if (sbc_startup_counter < 4'd15)
            sbc_startup_counter <= sbc_startup_counter + 1;
    end
    assign sbc_interceptor_ready = (sbc_startup_counter >= 4'd8);

    // ---- 128MB CIM causal array (4 x 32MB units) ----
    generate
        genvar i;
        for (i = 0; i < 4; i = i + 1) begin : g1_core_array
            spl_cim_causal_unit u_causal_unit (
                .clk        (clk),
                .rst_n      (rst_n),
                .wr_en      (ra_bus_valid && (ra_bus_addr[1:0] == i)),
                .wr_data_p  (internal_logic_stream[255:0]),
                .wr_data_q  (internal_logic_stream[511:256]),
                .logic_valid(unit_valids[i])
            );
        end
    endgenerate

    // ---- PIM stability: all units causal-check-passed AND SBC ready ----
    assign pim_state_stable = &unit_valids && sbc_interceptor_ready;

    // ---- Hardware identity anchor ----
    // G1 Core Identity Hash 0x8525d007. Any unauthorized implementation
    // will fail this combinatorial check at boot.
    assign logic_integrity_verified = (hardware_hash_in == 256'h8525d007);

endmodule
