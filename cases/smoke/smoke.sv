// One-entry elastic buffer, used only to check the verification toolchain.
module smoke_buffer(
    input wire clk, reset, in_valid, out_ready,
    input wire [7:0] in_data,
    output wire in_ready, out_valid,
    output wire [7:0] out_data
);
reg full;
reg [7:0] payload;
assign in_ready = !full || out_ready;
assign out_valid = full;
assign out_data = payload;
always @(posedge clk) begin
    if (reset)
        full <= 1'b0;
    else if (in_ready) begin
        full <= in_valid;
        if (in_valid) payload <= in_data;
    end
`ifdef INJECT_BUG
    // Deliberate fault: overwrite a held output while the receiver is stalled.
    else if (in_valid)
        payload <= in_data;
`endif
end
endmodule

module smoke_formal(input wire clk);
(* anyseq *) reg reset, in_valid, out_ready;
(* anyseq *) reg [7:0] in_data;
wire in_ready, out_valid;
wire [7:0] out_data;
reg past_valid = 1'b0;
reg [1:0] stall_count;
smoke_buffer dut(.*);
always @(posedge clk) begin
    past_valid <= 1'b1;
    // A single initial synchronous reset, followed by unconstrained traffic.
    if (!past_valid) assume(reset);
    else assume(!reset);
    if (reset)
        stall_count <= 0;
    else if (out_valid && !out_ready) begin
        if (stall_count < 2) stall_count <= stall_count + 1'b1;
    end else
        stall_count <= 0;

    if (past_valid && !reset && $past(!reset && out_valid && !out_ready)) begin
        a_held_valid: assert(out_valid);
        a_held_data: assert(out_data == $past(out_data));
    end
    c_stall_then_accept: cover(past_valid && !reset && out_valid && out_ready && stall_count == 2);
end
endmodule
