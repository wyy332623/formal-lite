// AXI bridge: convert class-SRAM slave requests into AXI master transactions.
module axi_bridge(
    // Common control: clock and active-low reset.
    input  wire        aclk,
    input  wire        aresetn,

    // IF-stage class-SRAM slave interface.
    input  wire        if_req,
    input  wire        if_wr,
    input  wire [ 1:0] if_size,
    input  wire [ 3:0] if_wstrb,
    input  wire [31:0] if_addr,
    input  wire [31:0] if_wdata,

    output wire        if_addr_ok,
    output wire        if_data_ok,
    output wire [31:0] if_rdata,

    // MEM-stage class-SRAM slave interface.
    input  wire        mem_req,
    input  wire        mem_wr,
    input  wire [ 1:0] mem_size,
    input  wire [ 3:0] mem_wstrb,
    input  wire [31:0] mem_addr,
    input  wire [31:0] mem_wdata,

    output wire        mem_addr_ok,
    output wire        mem_data_ok,
    output wire [31:0] mem_rdata,

    // AXI master interface.
    // Read address channel AR.
    output wire [ 3:0] arid,
    output wire [31:0] araddr,
    output wire [ 7:0] arlen,
    output wire [ 2:0] arsize,
    output wire [ 1:0] arburst,
    output wire [ 1:0] arlock,
    output wire [ 3:0] arcache,
    output wire [ 2:0] arprot,
    output wire        arvalid,
    input  wire        arready,

    // Read data channel R.
    input  wire [ 3:0] rid,
    input  wire [31:0] rdata,
    input  wire [ 1:0] rresp,
    input  wire        rlast,
    input  wire        rvalid,
    output wire        rready,

    // Write address channel AW.
    output wire [ 3:0] awid,
    output wire [31:0] awaddr,
    output wire [ 7:0] awlen,
    output wire [ 2:0] awsize,
    output wire [ 1:0] awburst,
    output wire [ 1:0] awlock,
    output wire [ 3:0] awcache,
    output wire [ 2:0] awprot,
    output wire        awvalid,
    input  wire        awready,

    // Write data channel W.
    output wire [ 3:0] wid,
    output wire [31:0] wdata,
    output wire [ 3:0] wstrb,
    output wire        wlast,
    output wire        wvalid,
    input  wire        wready,

    // Write response channel B.
    input  wire [ 3:0] bid,
    input  wire [ 1:0] bresp,
    input  wire        bvalid,
    output wire        bready
);

// Fixed / ignored signals.
assign arlen = 8'b0;
assign arburst = 2'b01;
assign arlock = 2'b0;
assign arcache = 4'b0;
assign arprot = 3'b0;
assign awid = 4'b1;
assign awlen = 8'b0;
assign awburst = 2'b01;
assign awlock = 2'b0;
assign awcache = 4'b0;
assign awprot = 3'b0;
assign wid = 4'b1;
assign wlast = 1'b1;

// Class-SRAM input buffers.
reg        if_pend;
reg [31:0] if_addr_r;
reg        mem_pend;
reg        mem_wr_r;
reg [ 2:0] mem_size_r;
reg [ 3:0] mem_wstrb_r;
reg [31:0] mem_addr_r;
reg [31:0] mem_wdata_r;

// addr_ok: latch the request into the bridge when its slot is empty.
assign if_addr_ok  = if_req  & ~if_pend;
assign mem_addr_ok = mem_req & ~mem_pend;

wire if_req_sent,mem_req_sent;
// Slave-side request handshake.
always @(posedge aclk) begin
    if (!aresetn) begin
        if_pend  <= 1'b0;
        mem_pend <= 1'b0;
    end
    else begin
        if (if_addr_ok) begin
            if_pend     <= 1'b1;
            if_addr_r   <= if_addr;
        end
        if (mem_addr_ok) begin
            mem_pend    <= 1'b1;
            mem_wr_r    <= mem_wr;
            mem_size_r  <= {1'b0,mem_size};
            mem_wstrb_r <= mem_wstrb;
            mem_addr_r  <= mem_addr;
            mem_wdata_r <= mem_wdata;
        end
        if (if_req_sent)  if_pend  <= 1'b0;
        if (mem_req_sent) mem_pend <= 1'b0;
    end
end


// Response slots: data_ok mirrors the slot valid bit.
// mem_rsp_vld is shared by read data and write completion (b_fire).
reg        if_rsp_vld;
reg [31:0] if_rdata_r;
reg        mem_rsp_vld;
reg [31:0] mem_rdata_r;
assign if_data_ok  = if_rsp_vld;
assign mem_data_ok = mem_rsp_vld;
assign if_rdata    = if_rdata_r;
assign mem_rdata   = mem_rdata_r;


always @(posedge aclk) begin
    if (!aresetn) begin
        if_rsp_vld  <= 1'b0;
        mem_rsp_vld <= 1'b0;
    end
    else begin
        if (r_fire) begin
            if(rid == 4'd0) begin
                if_rdata_r  <= rdata; if_rsp_vld  <= 1'b1;
            end
            if(rid == 4'd1) begin
                mem_rdata_r <= rdata; mem_rsp_vld <= 1'b1;
            end
        end
        if (b_fire) begin
            mem_rsp_vld <= 1'b1;
        end
        if (if_data_ok) begin
            if_rsp_vld  <= 1'b0;
        end
        if (mem_data_ok) begin
            mem_rsp_vld <= 1'b0;
        end
    end
end

reg wr_busy;
wire ar_fire,r_fire,aw_fire,w_fire,b_fire;
assign ar_fire = arvalid && arready;
assign  r_fire = rvalid  && rready;
assign aw_fire = awvalid && awready;
assign  w_fire = wvalid  && wready;
assign  b_fire = bvalid  && bready;
// Transaction busy state machine.
always @(posedge aclk) begin
    if (!aresetn) begin
        wr_busy <= 1'b0;
        rd_busy <= 1'b0;
    end
    else begin
        if (ar_fire) begin
            rd_busy <= 1'b1;
        end
        if (r_fire) begin
            rd_busy <= 1'b0;
        end
        if (aw_fire) begin
            wr_busy <= 1'b1;
        end
        if (w_fire) begin
            wr_busy <= 1'b1;
        end
        if (b_fire) begin
            wr_busy <= 1'b0;
        end
    end
end

// Arbitration signals (read priority: mem > if).
wire if_rd_req  = if_pend;
wire mem_rd_req = mem_pend   && !mem_wr_r;
wire wr_inflight = (mem_pend & mem_wr_r) | wr_busy;

// Master-side AR state machine.
reg [1:0] ar_state;
localparam AR_IDLE = 2'd0,AR_IF = 2'd1,AR_MEM = 2'd2;
always @(posedge aclk) begin
    if (!aresetn) begin
        ar_state <= AR_IDLE;
    end
    else begin
        case (ar_state)
            AR_IDLE: begin
                if (!wr_inflight) begin
                    if      (mem_rd_req) ar_state <= AR_MEM;   // data read has priority
                    else if (if_rd_req)  ar_state <= AR_IF;
                end
            end
            AR_IF, AR_MEM: begin
                if (arready) ar_state <= AR_IDLE;
            end
        endcase
    end
end

assign if_req_sent  = (ar_state == AR_IF) & arready;
assign mem_req_sent = ((ar_state == AR_MEM) & arready) | ((w_state == AW_FIRED) & w_fire) | ((w_state == W_FIRED) & aw_fire) | (aw_fire && w_fire);

assign arid   = (ar_state == AR_MEM) ? 1'b1 : 1'b0;
assign araddr = (ar_state == AR_IF) ? if_addr_r : mem_addr_r;
assign arsize = (ar_state == AR_IF) ? 3'd2 : mem_size_r;

// Master-side AW/W state machine.
reg [1:0] w_state;
localparam W_IDLE = 2'd0,AW_FIRED=2'd1,W_FIRED=2'd2,W_ALL_FIRED=2'd3;
always @(posedge aclk) begin
    if (!aresetn) begin
        w_state <= W_IDLE;
    end
    else begin
        case (w_state)
            W_IDLE: begin
                if(aw_fire && w_fire) w_state <= W_ALL_FIRED;
                else if (aw_fire)
                begin
                    w_state <= AW_FIRED;
                end
                else if (w_fire)
                begin
                    w_state <= W_FIRED;
                end
            end
            AW_FIRED: begin
                if(w_fire) w_state <= W_ALL_FIRED;
            end
            W_FIRED: begin
                if(aw_fire) w_state <= W_ALL_FIRED;
            end
            W_ALL_FIRED:begin
                if(b_fire)  w_state <= W_IDLE;
            end
        endcase
    end
end

// Master-side write signals.
assign awaddr = mem_addr_r;
assign awsize = mem_size_r;
assign wdata = mem_wdata_r;
assign wstrb = mem_wstrb_r;


// Valid and ready signals.
assign arvalid = ar_state == AR_IF | ar_state == AR_MEM;
assign rready  = 1'b1;
assign awvalid = ((w_state == W_IDLE) | (w_state == W_FIRED)) & mem_pend & mem_wr_r;
assign wvalid  = ((w_state == W_IDLE) | (w_state == AW_FIRED)) & mem_pend & mem_wr_r;
assign bready = 1'b1;



endmodule
