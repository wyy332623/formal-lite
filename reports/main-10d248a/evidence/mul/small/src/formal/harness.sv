// Port-only oracle: unsigned 32x32 product plus two's-complement correction.
// The DUT instead uses one signed 33x33 multiplication.
module mul_formal(input wire clk);
(* anyseq *) reg mul_signed;
(* anyseq *) reg [31:0] x, y;
wire [63:0] result;
mul dut(.mul_signed(mul_signed), .x(x), .y(y), .result(result));

wire [63:0] unsigned_product = {32'b0, x} * {32'b0, y};
wire [63:0] reference_product = unsigned_product
    - ((mul_signed && x[31]) ? {y, 32'b0} : 64'b0)
    - ((mul_signed && y[31]) ? {x, 32'b0} : 64'b0);
wire [63:0] checked_result;
`ifdef INJECT_CHECKER_FAULT
assign checked_result = result ^ 64'b1;
`else
assign checked_result = result;
`endif

always @(posedge clk) begin
`ifdef SMALL_OPERANDS
    // Full 32-bit DUT, restricted input domain only; no resized DUT.
    if (mul_signed) begin
        assume(x == {{24{x[7]}}, x[7:0]});
        assume(y == {{24{y[7]}}, y[7:0]});
    end else begin
        assume(x[31:8] == 0);
        assume(y[31:8] == 0);
    end
`endif
`ifndef CORNER_OPERAND
    a_product: assert(checked_result == reference_product);
`endif
    c_unsigned_high: cover(!mul_signed && x == 32'hffffffff && y == 32'hffffffff);
    c_signed_negative: cover(mul_signed && x == 32'h80000000 && y == 32'hffffffff);
    c_zero: cover(y == 0);
end
`ifdef CORNER_OPERAND
// 8 x 8 operand pairs, in both sign modes. These are finite full-width examples;
// they do not replace the arbitrary-operand proof above.
function [31:0] edge_value(input integer index);
    case (index)
        0: edge_value = 0;
        1: edge_value = 1;
        2: edge_value = 32'hffffffff;
        3: edge_value = 32'h80000000;
        4: edge_value = 32'h7fffffff;
        5: edge_value = 32'hffff0000;
        6: edge_value = 32'h00010000;
        7: edge_value = 32'haaaaaaaa;
    endcase
endfunction
genvar c;
generate for (c = 0; c < 128; c = c + 1) begin: corner
    localparam SIGNED_MODE = c % 2;
    localparam [31:0] X = edge_value((c / 2) / 8);
    localparam [31:0] Y = edge_value((c / 2) % 8);
    localparam signed [63:0] SX = {{32{X[31]}},X};
    localparam signed [63:0] SY = {{32{Y[31]}},Y};
    localparam signed [127:0] SIGNED_PRODUCT = SX * SY;
    localparam [63:0] UNSIGNED_PRODUCT = {32'b0,X} * {32'b0,Y};
    localparam [63:0] EXPECTED = SIGNED_MODE ? SIGNED_PRODUCT[63:0] : UNSIGNED_PRODUCT;
    wire [63:0] actual;
    mul instance_under_test(.mul_signed(SIGNED_MODE != 0), .x(X), .y(Y), .result(actual));
    always @(posedge clk) assert(actual == EXPECTED);
end endgenerate
`endif
endmodule
