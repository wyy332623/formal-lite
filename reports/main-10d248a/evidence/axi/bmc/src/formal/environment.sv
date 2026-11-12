// Legal stimulus assumptions. No DUT output is assumed to be correct.
reg f_past_valid = 1'b0;
reg [1:0] reset_phase = 0;
always @(posedge aclk) begin
    f_past_valid <= 1'b1;
    if (reset_phase < 2) reset_phase <= reset_phase + 1'b1;
    assume(aresetn == (reset_phase == 2));
    if (!aresetn) begin
        assume(!if_req && !mem_req && !rvalid && !bvalid);
    end else begin
`ifdef IF_ONLY
        assume(!mem_req);
`endif
        assume(!if_wr && if_size == 2 && if_wstrb == 0);
        assume(if_addr[1:0] == 0);
        assume(mem_size <= 2);
        if (mem_size == 2) assume(mem_addr[1:0] == 0);
        if (mem_size == 1) assume(mem_addr[0] == 0);
        if (mem_req && mem_wr) begin
            if (mem_size == 0) assume(mem_wstrb == (4'b0001 << mem_addr[1:0]));
            if (mem_size == 1) assume(mem_wstrb == (4'b0011 << mem_addr[1:0]));
            if (mem_size == 2) assume(mem_wstrb == 4'b1111);
        end
        // A source credit bound, not a bridge output assumption.
        if (if_count >= LIMIT) assume(!if_req);
        if (mem_count >= LIMIT) assume(!mem_req);
        if (rvalid) begin
            assume(rid == 0 || rid == 1);
            assume(rlast && rresp == 0);
            if (rid == 0) assume(if_rd_count > 0);
            else assume(mem_rd_count > 0);
        end
        if (bvalid) assume(bid == 1 && bresp == 0 && wr_count > 0);
    end
    if (f_past_valid && aresetn && $past(aresetn)) begin
        if ($past(rvalid && !rready)) begin
            assume(rvalid);
            assume($stable({rid, rdata, rresp, rlast}));
        end
        if ($past(bvalid && !bready)) begin
            assume(bvalid);
            assume($stable({bid, bresp}));
        end
    end
end
