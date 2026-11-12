`timescale 1ns/1ps
// Deterministic port-only replay of the two formal counterexamples.
// Compiled against the Yosys-exported netlist of unmodified pinned RTL.
module replay_tb;
reg clk = 0;
always #5 clk = ~clk;
reg resetn = 0;
reg if_req = 0, mem_req = 0, mem_wr = 0;
reg [31:0] if_addr = 0, mem_addr = 32'h2000;
reg [3:0] rid = 0;
reg [31:0] rdata = 0;
reg rvalid = 0, bvalid = 0;
wire if_addr_ok, if_data_ok, mem_addr_ok, mem_data_ok;
wire arvalid, awvalid, wvalid;
wire [3:0] arid;
integer if_completions = 0;
integer mem_completions = 0;

axi_bridge dut(
    .aclk(clk), .aresetn(resetn),
    .if_req(if_req), .if_wr(1'b0), .if_size(2'd2), .if_wstrb(4'b0),
    .if_addr(if_addr), .if_wdata(32'b0), .if_addr_ok(if_addr_ok), .if_data_ok(if_data_ok),
    .mem_req(mem_req), .mem_wr(mem_wr), .mem_size(2'd2), .mem_wstrb(4'hf),
    .mem_addr(mem_addr), .mem_wdata(32'h1234abcd),
    .mem_addr_ok(mem_addr_ok), .mem_data_ok(mem_data_ok),
    .arid(arid), .arvalid(arvalid), .arready(1'b1),
    .rid(rid), .rdata(rdata), .rresp(2'b0), .rlast(1'b1), .rvalid(rvalid),
    .awvalid(awvalid), .awready(1'b1), .wvalid(wvalid), .wready(1'b1),
    .bid(4'd1), .bresp(2'b0), .bvalid(bvalid)
);

always @(posedge clk) begin
    if (!resetn) begin
        if_completions = 0;
        mem_completions = 0;
    end else begin
        if (if_data_ok) if_completions = if_completions + 1;
        if (mem_data_ok) mem_completions = mem_completions + 1;
    end
end

task reset_all;
begin
    @(negedge clk);
    resetn = 0; if_req = 0; mem_req = 0; rvalid = 0; bvalid = 0;
    repeat (2) @(posedge clk);
    @(negedge clk); resetn = 1;
end
endtask

task send_if;
begin
    @(negedge clk); if_req = 1;
    @(posedge clk);
    while (!if_addr_ok) @(posedge clk);
    @(negedge clk); if_req = 0;
    while (!arvalid) @(negedge clk);
    if (arid != 0) $fatal(1, "Unexpected IF ARID");
    @(posedge clk);
    @(negedge clk); if_addr = if_addr + 4;
end
endtask

initial begin
    $dumpfile("replay.vcd");
    $dumpvars(0, replay_tb);
    // Earlier MEM read is still awaiting R when a later write receives B.
    reset_all;
    @(negedge clk); mem_req = 1; mem_wr = 0;
    @(posedge clk);
    while (!mem_addr_ok) @(posedge clk);
    @(negedge clk); mem_req = 0;
    while (!arvalid) @(negedge clk);
    if (arid != 1) $fatal(1, "Unexpected MEM ARID");
    @(posedge clk);
    @(negedge clk); mem_req = 1; mem_wr = 1;
    @(posedge clk);
    while (!mem_addr_ok) @(posedge clk);
    @(negedge clk); mem_req = 0;
    while (!(awvalid && wvalid)) @(negedge clk);
    @(posedge clk);
    @(negedge clk); bvalid = 1;
    @(posedge clk);
    @(negedge clk); bvalid = 0;
    if (!mem_data_ok) $fatal(1, "Expected order violation did not reproduce");
    $display("REPRODUCED: later MEM write completes before earlier read response");

    // Two prior IF ARs, then two legal, consecutive RID=0 responses.
    reset_all;
    send_if;
    send_if;
    @(negedge clk); rid = 0; rvalid = 1; rdata = 32'h11111111;
    @(posedge clk);
    @(negedge clk); rdata = 32'h22222222;
    @(posedge clk);
    @(negedge clk); rvalid = 0;
    repeat (6) @(negedge clk);
    if (if_completions != 1) $fatal(1, "Expected lost response did not reproduce: %0d completions", if_completions);
    $display("REPRODUCED: two consecutive IF R responses yield only %0d completion", if_completions);
    $display("REPLAY CONFIRMED TWO DESIGN FAILURES; this is not a DUT pass");
    $finish;
end

initial begin
    #3000;
    $fatal(1, "Replay watchdog expired");
end
endmodule
