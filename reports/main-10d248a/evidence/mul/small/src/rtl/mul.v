// Textbook 6.2.1.1: one combinational 33-bit signed multiplication also
// handles unsigned operands by zero-extending them. No extra EX cycle.
module mul(
    input  wire mul_signed,
    input  wire [31:0] x,
    input  wire [31:0] y,
    output wire [63:0] result
);
wire signed [32:0] x_ext = {mul_signed && x[31], x};
wire signed [32:0] y_ext = {mul_signed && y[31], y};
wire signed [65:0] product;

assign product = x_ext * y_ext;

assign result = product[63:0];

endmodule
