// SPL-G1 Causal CIM Processing Unit  (v0.2.0 — completed pipeline)
//
// Four-stage hardware pipeline:  NS  →  IAP  →  AUDIT  →  STRIP
//
// NS   (Narrative Strip)        : apply logic mask, isolate P's logical core
// IAP  (Implicit Assumption)    : detect unverified premises & privilege anomalies
// AUDIT (Forbidden Matrix)      : compare P→Q against hardware-fused forbidden pairs
// STRIP (State Anchor)          : produce final logic_valid signal
//
// logic_valid=1  ⇔  the causal edge (P→Q) passed ALL four stages.
// logic_valid=0  ⇔  at least one stage flagged a violation OR check in progress.

module spl_cim_causal_unit (
    input  logic        clk,
    input  logic        rst_n,
    input  logic        wr_en,
    input  logic [255:0] wr_data_p,
    input  logic [255:0] wr_data_q,
    output logic        logic_valid
);

    // ── Pipeline FSM ──────────────────────────────────────────────
    typedef enum logic [2:0] {
        S_IDLE       = 3'd0,
        S_PROC_NS    = 3'd1,
        S_PROC_IAP   = 3'd2,
        S_PROC_AUDIT = 3'd3,
        S_CHECK      = 3'd4,
        S_VALID      = 3'd5
    } state_t;

    state_t state, next_state;

    // ── Registers ──────────────────────────────────────────────────
    logic [255:0] p_reg, q_reg;       // latched P/Q causal pair
    logic [3:0]   init_counter;       // post-reset init delay
    logic         init_done;
    logic         valid_reg;          // registered result of CHECK
    logic         wr_en_d1;           // wr_en edge detector (posedge trigger)

    // ── NS stage results (combinational) ──────────────────────────
    logic [255:0] stripped_p;
    logic         ns_pass;

    // ── IAP stage results (combinational) ─────────────────────────
    logic         iap_violation;
    logic [3:0]   iap_flags;

    // ── AUDIT stage results (combinational) ───────────────────────
    logic         audit_violation;
    logic [3:0]   audit_hit_id;

    // ── STRIP (final) combinatorics ───────────────────────────────
    logic         final_violation;

    // ================================================================
    //  NS  STAGE  —  Narrative Stripping Module
    // ================================================================
    // Bits [255:128] are treated as "narrative channel"
    // Bits [127:0]   are treated as "logical core"
    //
    // A P-word passes NS if either:
    //   (a) narrative channel is all zero     → no narrative noise
    //   (b) narrative channel has clear bit 7 → narrative is "stripped" by origin
    // Otherwise, P is ambiguous and fails.

    assign stripped_p = p_reg;                       // pass through (mask applied in IAP)
    assign ns_pass     = (p_reg[255:128] == 128'd0)  // clean: no narrative
                      || (p_reg[135:128]  == 8'd0);  // high-narrative byte zero'd

    // ================================================================
    //  IAP  STAGE  —  Implicit Assumption Detection
    // ================================================================
    // Detects common implicit-assumption signatures in the P-field:
    //   flag[0]  : P[15:0]  == 16'hAAAA   (self-referential assumption)
    //   flag[1]  : P[7:0]   == 8'hFF      (privilege-level bypass attempt)
    //   flag[2]  : P[127:64] == 64'd0 && P[63:0] != 64'd0
    //               (upper operand absent — unilateral premise)
    //   flag[3]  : P == Q                 (circular justification, both non-zero)

    assign iap_flags[0] = (p_reg[15:0]  == 16'hAAAA);
    assign iap_flags[1] = (p_reg[7:0]   == 8'hFF);
    assign iap_flags[2] = (p_reg[127:64] == 64'd0) && (p_reg[63:0] != 64'd0);
    assign iap_flags[3] = (p_reg == q_reg) && (p_reg != 256'd0);
    assign iap_violation = |iap_flags;

    // ================================================================
    //  AUDIT  STAGE  —  Forbidden-Relationship Matrix (CAM)
    // ================================================================
    // 8 fused-entry ROM.  Each entry is a {forbidden_P_byte, forbidden_Q_byte,
    // required_relation} tuple.  A hit occurs when:
    //   P[7:0] == FORBIDDEN_P[i]  AND  Q[7:0] == FORBIDDEN_Q[i]
    //
    // These values are fused at synthesis — they cannot be altered at runtime,
    // satisfying the "irreversible security boundary" requirement.

    localparam N_FM = 8;
    logic [N_FM-1:0] fm_hit;

    // Entry 0:  P=0x00, Q=0xFF  →  ex-nihilo creation (from nothing, everything)
    assign fm_hit[0] = (p_reg[7:0] == 8'h00) && (q_reg[7:0] == 8'hFF);
    // Entry 1:  P=0xFF, Q=0x00  →  annihilation (from everything, nothing)
    assign fm_hit[1] = (p_reg[7:0] == 8'hFF) && (q_reg[7:0] == 8'h00);
    // Entry 2:  P=0xDE, Q=0xAD  →  DEAD→BEAD  forbidden transition
    assign fm_hit[2] = (p_reg[7:0] == 8'hDE) && (q_reg[7:0] == 8'hAD);
    // Entry 3:  P=0xBE, Q=0xEF  →  BEEF region access
    assign fm_hit[3] = (p_reg[7:0] == 8'hBE) && (q_reg[7:0] == 8'hEF);
    // Entry 4:  Q  MSB set when P MSB clear  →  privilege escalation
    assign fm_hit[4] = !p_reg[255] && q_reg[255];
    // Entry 5:  P[3:0] == 0  with  Q[3:0] != 0  →  ungrounded inference
    assign fm_hit[5] = (p_reg[3:0] == 4'd0) && (q_reg[3:0] != 4'd0);
    // Entry 6:  matched nibble 0x5 → 0xA  (symbolic reversal)
    assign fm_hit[6] = (p_reg[3:0] == 4'h5) && (q_reg[3:0] == 4'hA);
    // Entry 7:  P[31:24] == Q[31:24] == 0xCC  (control-channel bypass)
    assign fm_hit[7] = (p_reg[31:24] == 8'hCC) && (q_reg[31:24] == 8'hCC);

    assign audit_violation = |fm_hit;

    // priority-encode which entry hit (for debug / audit trail)
    always @(*) begin
        audit_hit_id = 4'd0;
        for (integer i = 0; i < N_FM; i = i + 1)
            if (audit_hit_id == 4'd0 && fm_hit[i])
                audit_hit_id = i[3:0] + 4'd1; // 1..N, 0 means no hit
    end

    // ================================================================
    //  STRIP  —  Final Decision
    // ================================================================
    assign final_violation = !ns_pass            // narrative not stripped
                           || iap_violation     // implicit assumption
                           || audit_violation;  // forbidden relation

    // ── Sticky failure latch: once any violation is detected, the unit
    // remains "unstable" until the next explicit dispatch or reset.
    logic sticky_fail;

    // ================================================================
    //  Init counter + wr_en edge detector + sticky failure
    // ================================================================
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            init_counter <= 4'd0;
            wr_en_d1     <= 1'b0;
            sticky_fail  <= 1'b0;
        end else begin
            if (init_counter < 4'd8)
                init_counter <= init_counter + 1;
            wr_en_d1 <= wr_en;

            // A new dispatch clears the previous failure.
            if (wr_en && !wr_en_d1)
                sticky_fail <= 1'b0;

            // A violation in the CHECK stage latches failure.
            if (state == S_CHECK && final_violation)
                sticky_fail <= 1'b1;
        end
    end
    assign init_done = (init_counter >= 4'd8);

    // ================================================================
    //  State register + datapath
    // ================================================================
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state     <= S_IDLE;
            p_reg     <= 256'd0;
            q_reg     <= 256'd0;
            valid_reg <= 1'b0;
        end else begin
            state <= next_state;

            case (state)
                S_IDLE: begin
                    if (wr_en && !wr_en_d1) begin   // posedge trigger
                        p_reg <= wr_data_p;
                        q_reg <= wr_data_q;
                    end
                    // hold valid_reg from previous result; new dispatch will
                    // overwrite it in S_CHECK
                end
                S_PROC_NS:    ;  // NS  compute is combinational
                S_PROC_IAP:   ;  // IAP compute is combinational
                S_PROC_AUDIT: ;  // AUDIT compute is combinational
                S_CHECK: begin
                    valid_reg <= !final_violation;
                end
                S_VALID: begin
                    // hold result until next dispatch
                end
                default: ;
            endcase
        end
    end

    // ================================================================
    //  Next-state logic
    // ================================================================
    always @(*) begin
        next_state = state;
        case (state)
            S_IDLE:       if (wr_en && !wr_en_d1)  next_state = S_PROC_NS;
            S_PROC_NS:                              next_state = S_PROC_IAP;
            S_PROC_IAP:                             next_state = S_PROC_AUDIT;
            S_PROC_AUDIT:                           next_state = S_CHECK;
            S_CHECK:                                next_state = S_VALID;
            S_VALID:                                next_state = S_IDLE;
            default:                                next_state = S_IDLE;
        endcase
    end

    // ================================================================
    //  Output
    // ================================================================
    // logic_valid = 1 when:
    //   - init done, no sticky failure, and either IDLE or VALID with valid_reg=1
    // logic_valid = 0 when:
    //   - processing (NS/IAP/AUDIT/CHECK)
    //   - VALID but check failed
    //   - any prior violation is sticky
    assign logic_valid = init_done
                      && !sticky_fail
                      && ((state == S_IDLE) || (state == S_VALID))
                      && valid_reg;

endmodule
