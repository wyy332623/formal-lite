// Independent external transaction/latency model, no DUT internal references.
module div_formal(input wire div_clk);
(* anyseq *) reg resetn, cancel, request;
`ifdef CORNER_VECTORS
(* anyconst *) reg [2:0] vector_id;
reg div_signed;
reg [31:0] x, y, vector_s, vector_r;
// Explicit mathematical examples, not an implementation of division.
always @* begin
    case (vector_id)
        0: begin div_signed=1; x=32'hfffffff9; y=3; vector_s=32'hfffffffe; vector_r=32'hffffffff; end
        1: begin div_signed=1; x=7; y=32'hfffffffd; vector_s=32'hfffffffe; vector_r=1; end
        2: begin div_signed=1; x=32'h80000000; y=32'hffffffff; vector_s=32'h80000000; vector_r=0; end
        3: begin div_signed=1; x=32'h80000000; y=1; vector_s=32'h80000000; vector_r=0; end
        4: begin div_signed=0; x=32'hffffffff; y=32'h80000000; vector_s=1; vector_r=32'h7fffffff; end
        5: begin div_signed=0; x=32'hffffffff; y=2; vector_s=32'h7fffffff; vector_r=1; end
        6: begin div_signed=1; x=32'hfffffff9; y=0; vector_s=32'hffffffff; vector_r=32'hfffffff9; end
        7: begin div_signed=0; x=32'hffffffff; y=0; vector_s=32'hffffffff; vector_r=32'hffffffff; end
    endcase
end
`else
(* anyseq *) reg div_signed;
(* anyseq *) reg [31:0] x, y;
`endif
wire [31:0] s, r;
wire complete;
div dut(.div_clk(div_clk), .resetn(resetn), .cancel(cancel),
        .div(request), .div_signed(div_signed), .x(x), .y(y),
        .s(s), .r(r), .complete(complete));

reg past_valid = 0;
reg [1:0] reset_phase = 0;
reg running, held;
reg [5:0] age;
wire accept = resetn && !cancel && request && !running && !held;
wire finishing = resetn && !cancel && running && age == 31;
reg [31:0] launch_x, launch_y;
reg launch_signed;
reg saw_cancel, saw_completion;
reg [2:0] hold_cycles;

`ifndef CONTROL_ONLY
wire negative_x = div_signed && x[31];
wire negative_y = div_signed && y[31];
wire [31:0] magnitude_x = negative_x ? -x : x;
wire [31:0] magnitude_y = negative_y ? -y : y;
// Division/modulo oracle is unrelated to the DUT's bit-by-bit algorithm.
wire [31:0] quotient_magnitude = magnitude_y != 0 ? magnitude_x / magnitude_y : 32'hffffffff;
wire [31:0] remainder_magnitude = magnitude_y != 0 ? magnitude_x % magnitude_y : magnitude_x;
`ifdef CORNER_VECTORS
wire [31:0] expected_quotient = vector_s;
wire [31:0] expected_remainder = vector_r;
`else
wire [31:0] expected_quotient = (negative_x ^ negative_y) && y != 0 ? -quotient_magnitude : quotient_magnitude;
wire [31:0] expected_remainder = negative_x ? -remainder_magnitude : remainder_magnitude;
`endif
reg [31:0] pending_s, pending_r, model_s, model_r;
`endif

always @(posedge div_clk) begin
    past_valid <= 1;
    if (reset_phase < 2) reset_phase <= reset_phase + 1'b1;
    // First two edges reset. Later resets remain arbitrary, including mid-operation.
    if (reset_phase < 2) assume(!resetn);
`ifdef SMALL_OPERANDS
    if (accept) begin
        if (div_signed) begin
            assume(x == {{24{x[7]}}, x[7:0]});
            assume(y == {{24{y[7]}}, y[7:0]});
        end else begin
            assume(x[31:8] == 0);
            assume(y[31:8] == 0);
        end
    end
`endif
`ifdef ZERO_DIVISOR
    if (accept) assume(y == 0);
`endif
`ifdef UNIT_DIVISOR
    if (accept) assume(y == 1 || y == 32'hffffffff);
`endif

    if (!resetn) begin
        running <= 0;
        held <= 0;
        age <= 0;
        saw_cancel <= 0;
        saw_completion <= 0;
        hold_cycles <= 0;
`ifndef CONTROL_ONLY
        pending_s <= 0; pending_r <= 0;
        model_s <= 0; model_r <= 0;
`endif
    end else if (cancel) begin
        running <= 0;
        held <= 0;
        if (running) saw_cancel <= 1;
        hold_cycles <= 0;
    end else begin
        if (!request) held <= 0;
        if (held && request) begin
            if (hold_cycles < 4) hold_cycles <= hold_cycles + 1'b1;
        end else hold_cycles <= 0;
        if (accept) begin
            running <= 1;
            held <= 0;
            age <= 0;
            launch_x <= x; launch_y <= y; launch_signed <= div_signed;
`ifndef CONTROL_ONLY
            pending_s <= expected_quotient;
            pending_r <= expected_remainder;
`endif
        end else if (running) begin
            if (age == 31) begin
                running <= 0;
                held <= 1;
                saw_completion <= 1;
`ifndef CONTROL_ONLY
                model_s <= pending_s;
                model_r <= pending_r;
`endif
            end else age <= age + 1'b1;
        end
    end

    if (past_valid) begin
        // This checks latency and absence of unsolicited/stale completions.
        a_complete_timing: assert(complete == held);
        if ($past(!resetn)) begin
            a_reset_outputs: assert(s == 0 && r == 0 && !complete);
        end
        if ($past(resetn && cancel)) begin
            a_cancel_complete: assert(!complete);
            a_cancel_retains_data: assert($stable({s,r}));
        end
        if ($past(resetn && !finishing)) begin
            a_result_changes_only_on_finish: assert($stable({s,r}));
        end
        if ($past(resetn && !cancel && held && request)) begin
            a_hold_complete: assert(complete);
            a_hold_data: assert($stable({s,r}));
        end
`ifndef CONTROL_ONLY
`ifdef INJECT_CHECKER_FAULT
        if (complete) a_arithmetic: assert((s ^ 32'b1) == model_s && r == model_r);
`else
        a_arithmetic: assert(s == model_s && r == model_r);
`endif
`endif
    end
    c_complete: cover(past_valid && complete);
    c_hold: cover(past_valid && complete && hold_cycles == 3);
    c_cancel_last: cover(past_valid && resetn && cancel && running && age == 31);
    c_restart_after_cancel: cover(past_valid && saw_cancel && complete);
    c_second_operation: cover(past_valid && saw_completion && accept);
`ifndef CONTROL_ONLY
    c_divide_by_zero: cover(past_valid && resetn && complete && launch_y == 0);
    c_signed_overflow: cover(past_valid && resetn && complete && launch_signed && launch_x == 32'h80000000 && launch_y == 32'hffffffff);
    c_signed_negative: cover(past_valid && resetn && complete && launch_signed && launch_x == 32'hfffffff9 && launch_y == 3);
`endif
end
`ifdef CORNER_VECTORS
genvar v;
generate for (v = 0; v < 8; v = v + 1) begin: vector_reachability
    always @(posedge div_clk) cover(past_valid && resetn && complete && vector_id == v);
end endgenerate
`endif
endmodule
