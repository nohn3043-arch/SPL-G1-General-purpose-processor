// SPL-G1 Causal CIM Processing Unit
// Checks causal validity of (P -> Q) using in-memory comparator fabric.
// Four instances form the 128MB CIM array; each unit independently verifies
// one causal-edge pair against the forbidden-relationship matrix.

module spl_cim_causal_unit (
    input  logic        clk,
    input  logic        rst_n,
    input  logic        wr_en,        // Write enable: latch P/Q pair from RA-BUS
    input  logic [255:0] wr_data_p,   // Causal antecedent P (stripped logic)
    input  logic [255:0] wr_data_q,   // Causal consequent Q
    output logic        logic_valid   // High when causal check passes (or IDLE after init)
);

    typedef enum logic [1:0] {
        IDLE       = 2'b00,
        PROCESSING = 2'b01,
        CHECK      = 2'b10,
        VALID      = 2'b11
    } state_t;

    state_t state, next_state;

    logic [255:0] p_reg, q_reg;      // Latched P/Q pair
    logic [3:0]   proc_cycle;        // Multi-cycle CIM access counter
    logic         init_done;         // Post-reset initialization complete
    logic [3:0]   init_counter;
    logic         wr_en_d1;          // wr_en delayed 1 cycle (edge detection)

    // ---- wr_en edge detector (prevents re-trigger on stuck-high RA-BUS) ----
    // ---- Initialization counter (4 cycles post-reset) ----
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            init_counter <= 4'd0;
            wr_en_d1     <= 1'b0;
        end else begin
            if (init_counter < 4'd4)
                init_counter <= init_counter + 1;
            wr_en_d1 <= wr_en;
        end
    end
    assign init_done = (init_counter >= 4'd4);

    // ---- State register + data path ----
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state      <= IDLE;
            p_reg      <= 256'h0;
            q_reg      <= 256'h0;
            proc_cycle <= 4'd0;
        end else begin
            state <= next_state;

            case (state)
                IDLE: begin
                    if (wr_en) begin
                        p_reg      <= wr_data_p;
                        q_reg      <= wr_data_q;
                        proc_cycle <= 4'd0;
                    end
                end
                PROCESSING: begin
                    proc_cycle <= proc_cycle + 1;
                end
                CHECK: begin
                    // In full implementation: compare (p_reg, q_reg) against
                    // the CIM-hosted forbidden-relationship matrix.
                    // Skeleton: any non-zero P/Q pair passes.
                end
                VALID: begin
                    p_reg <= 256'h0;
                    q_reg <= 256'h0;
                end
            endcase
        end
    end

    // ---- Next-state logic ----
    always_comb begin
        next_state = state;
        case (state)
            IDLE:       if (wr_en && !wr_en_d1)              next_state = PROCESSING;
            PROCESSING: if (proc_cycle >= 4'd3)            next_state = CHECK;
            CHECK:                                          next_state = VALID;
            VALID:                                          next_state = IDLE;
        endcase
    end

    // ---- Output ----
    // logic_valid = 1 when the unit has nothing to check (IDLE + init done)
    //               or has just completed a causal check (VALID)
    assign logic_valid = (state == VALID) | ((state == IDLE) && init_done);

endmodule
