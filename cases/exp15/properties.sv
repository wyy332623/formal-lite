`ifndef REQUEST_LIMIT
`define REQUEST_LIMIT 2
`endif
localparam LIMIT = `REQUEST_LIMIT;
// Independent transaction ledger; no references to DUT state.
reg [2:0] if_count, mem_count, if_wait_issue, mem_wait_issue;
reg if_tail, if_head, if_issue, mem_tail, mem_head, mem_issue;
reg [31:0] if_address [0:1];
reg [31:0] mem_address [0:1];
reg [1:0] mem_size_q [0:1];
reg mem_write_q [0:1];
reg [31:0] mem_write_data [0:1];
reg [3:0] mem_mask [0:1];
reg [1:0] if_done, mem_done;
reg [31:0] if_expected_data [0:1];
reg [31:0] mem_expected_data [0:1];
reg [2:0] if_rd_count, mem_rd_count, wr_count;
reg if_rd_tail, if_rd_head, mem_rd_tail, mem_rd_head, wr_tail, wr_head;
reg if_rd_token [0:1];
reg mem_rd_token [0:1];
reg wr_token [0:1];
reg aw_seen, w_seen;
wire if_accept = if_req && if_addr_ok;
wire mem_accept = mem_req && mem_addr_ok;
wire ar_hs = arvalid && arready;
wire if_ar_hs = ar_hs && arid == 0;
wire mem_ar_hs = ar_hs && arid == 1;
wire aw_hs = awvalid && awready;
wire w_hs = wvalid && wready;
wire r_hs = rvalid && rready;
wire if_r_hs = r_hs && rid == 0;
wire mem_r_hs = r_hs && rid == 1;
wire b_hs = bvalid && bready;
wire write_issued = (aw_seen || aw_hs) && (w_seen || w_hs) && (aw_hs || w_hs);
wire mem_issued = mem_ar_hs || write_issued;
wire if_current_response = if_r_hs && if_rd_token[if_rd_head] == if_head;
wire mem_current_read = mem_r_hs && mem_rd_token[mem_rd_head] == mem_head;
wire mem_current_write = b_hs && wr_token[wr_head] == mem_head;
reg [2:0] ar_stalls, write_stalls;
reg saw_aw_first, saw_w_first, saw_read_then_write;
reg previous_mem_r;

always @(posedge aclk) begin
    if (!aresetn) begin
        if_count <= 0; mem_count <= 0;
        if_wait_issue <= 0; mem_wait_issue <= 0;
        if_tail <= 0; if_head <= 0; if_issue <= 0;
        mem_tail <= 0; mem_head <= 0; mem_issue <= 0;
        if_done <= 0; mem_done <= 0;
        if_rd_count <= 0; mem_rd_count <= 0; wr_count <= 0;
        if_rd_tail <= 0; if_rd_head <= 0;
        mem_rd_tail <= 0; mem_rd_head <= 0; wr_tail <= 0; wr_head <= 0;
        aw_seen <= 0; w_seen <= 0;
        ar_stalls <= 0; write_stalls <= 0;
        saw_aw_first <= 0; saw_w_first <= 0; saw_read_then_write <= 0;
        previous_mem_r <= 0;
    end else begin
        if_count <= if_count + if_accept - if_data_ok;
        mem_count <= mem_count + mem_accept - mem_data_ok;
        if_wait_issue <= if_wait_issue + if_accept - if_ar_hs;
        mem_wait_issue <= mem_wait_issue + mem_accept - mem_issued;
        if (if_accept) begin
            if_address[if_tail] <= if_addr;
            if_done[if_tail] <= 0;
            if_tail <= !if_tail;
        end
        if (mem_accept) begin
            mem_address[mem_tail] <= mem_addr;
            mem_size_q[mem_tail] <= mem_size;
            mem_write_q[mem_tail] <= mem_wr;
            mem_write_data[mem_tail] <= mem_wdata;
            mem_mask[mem_tail] <= mem_wstrb;
            mem_done[mem_tail] <= 0;
            mem_tail <= !mem_tail;
        end
        if (if_ar_hs) if_issue <= !if_issue;
        if (mem_issued) mem_issue <= !mem_issue;
        if (aw_hs) aw_seen <= 1;
        if (w_hs) w_seen <= 1;
        if (write_issued) begin aw_seen <= 0; w_seen <= 0; end
        if_rd_count <= if_rd_count + if_ar_hs - if_r_hs;
        mem_rd_count <= mem_rd_count + mem_ar_hs - mem_r_hs;
        wr_count <= wr_count + write_issued - b_hs;
        if (if_ar_hs) begin
            if_rd_token[if_rd_tail] <= if_issue;
            if_rd_tail <= !if_rd_tail;
        end
        if (mem_ar_hs) begin
            mem_rd_token[mem_rd_tail] <= mem_issue;
            mem_rd_tail <= !mem_rd_tail;
        end
        if (write_issued) begin
            wr_token[wr_tail] <= mem_issue;
            wr_tail <= !wr_tail;
        end
        if (if_r_hs) begin
            if_rd_head <= !if_rd_head;
            if_done[if_rd_token[if_rd_head]] <= 1;
            if_expected_data[if_rd_token[if_rd_head]] <= rdata;
        end
        if (mem_r_hs) begin
            mem_rd_head <= !mem_rd_head;
            mem_done[mem_rd_token[mem_rd_head]] <= 1;
            mem_expected_data[mem_rd_token[mem_rd_head]] <= rdata;
        end
        if (b_hs) begin
            wr_head <= !wr_head;
            mem_done[wr_token[wr_head]] <= 1;
        end
        if (if_data_ok) begin
            if_head <= !if_head;
            if_done[if_head] <= 0;
        end
        if (mem_data_ok) begin
            mem_head <= !mem_head;
            mem_done[mem_head] <= 0;
        end
        if (arvalid && !arready) begin
            if (ar_stalls < 4) ar_stalls <= ar_stalls + 1'b1;
        end else ar_stalls <= 0;
        if ((awvalid && !awready) || (wvalid && !wready)) begin
            if (write_stalls < 4) write_stalls <= write_stalls + 1'b1;
        end else write_stalls <= 0;
        if (aw_hs && !w_hs && !w_seen) saw_aw_first <= 1;
        if (w_hs && !aw_hs && !aw_seen) saw_w_first <= 1;
        if (write_issued && mem_rd_count != 0) saw_read_then_write <= 1;
        previous_mem_r <= mem_r_hs;
    end
end

always @(posedge aclk) begin
    if (f_past_valid && $past(!aresetn)) begin
        a_reset_valid: assert(!arvalid && !awvalid && !wvalid);
        a_reset_response: assert(!if_data_ok && !mem_data_ok);
    end
    if (f_past_valid && aresetn && $past(aresetn)) begin
        if ($past(arvalid && !arready)) begin
            a_arvalid_hold: assert(arvalid);
            a_ar_payload_hold: assert($stable({arid,araddr,arlen,arsize,arburst,arlock,arcache,arprot}));
        end
        if ($past(awvalid && !awready)) begin
            a_awvalid_hold: assert(awvalid);
            a_aw_payload_hold: assert($stable({awid,awaddr,awlen,awsize,awburst,awlock,awcache,awprot}));
        end
        if ($past(wvalid && !wready)) begin
            a_wvalid_hold: assert(wvalid);
            a_w_payload_hold: assert($stable({wid,wdata,wstrb,wlast}));
        end
    end
    if (aresetn) begin
        a_fixed_read: assert(arlen == 0 && arburst == 1 && arlock == 0);
        a_fixed_write: assert(awlen == 0 && awburst == 1 && awid == 1 && wid == 1 && wlast);
`ifndef STABILITY_ONLY
        a_if_capacity: assert(if_count <= LIMIT && if_wait_issue <= if_count);
        a_mem_capacity: assert(mem_count <= LIMIT && mem_wait_issue <= mem_count);
        a_axi_capacity: assert(if_rd_count <= LIMIT && mem_rd_count <= LIMIT && wr_count <= LIMIT);
        if (ar_hs) begin
            a_ar_id: assert(arid == 0 || arid == 1);
            if (arid == 0) begin
                a_if_ar_exists: assert(if_wait_issue > 0);
                a_if_ar_payload: assert(araddr == if_address[if_issue] && arsize == 2);
            end else begin
                a_mem_ar_exists: assert(mem_wait_issue > 0 && !mem_write_q[mem_issue]);
                a_mem_ar_payload: assert(araddr == mem_address[mem_issue] && arsize == {1'b0,mem_size_q[mem_issue]});
            end
        end
        if (aw_hs) begin
            a_aw_exists: assert(mem_wait_issue > 0 && mem_write_q[mem_issue] && !aw_seen);
            a_aw_payload: assert(awaddr == mem_address[mem_issue] && awsize == {1'b0,mem_size_q[mem_issue]});
        end
        if (w_hs) begin
            a_w_exists: assert(mem_wait_issue > 0 && mem_write_q[mem_issue] && !w_seen);
            a_w_payload: assert(wdata == mem_write_data[mem_issue] && wstrb == mem_mask[mem_issue]);
        end
        if (if_data_ok) begin
            a_if_response_exists: assert(if_count > 0 && (if_done[if_head] || if_current_response));
            a_if_response_data: assert(if_rdata == (if_done[if_head] ? if_expected_data[if_head] : rdata));
        end
        if (mem_data_ok) begin
            a_mem_response_exists: assert(mem_count > 0 && (mem_done[mem_head] || mem_current_read || mem_current_write));
            if (!mem_write_q[mem_head]) begin
                a_mem_response_data: assert(mem_rdata == (mem_done[mem_head] ? mem_expected_data[mem_head] : rdata));
            end
        end
`endif
        c_both_request: cover(if_accept && mem_accept);
        c_aw_first_completed: cover(saw_aw_first && b_hs);
        c_w_first_completed: cover(saw_w_first && b_hs);
        c_ar_long_stall: cover(ar_stalls >= 3 && ar_hs);
        c_write_long_stall: cover(write_stalls >= 3 && write_issued);
        c_if_response: cover(if_data_ok);
        c_mem_read_response: cover(mem_data_ok && !mem_write_q[mem_head]);
        c_mem_write_response: cover(mem_data_ok && mem_write_q[mem_head]);
        c_cross_read_write: cover(saw_read_then_write && b_hs);
`ifdef COVER_PIPELINED
        c_same_id_adjacent_responses: cover(previous_mem_r && mem_r_hs);
        c_parallel_mem_responses: cover(mem_r_hs && b_hs);
`endif
    end
end
