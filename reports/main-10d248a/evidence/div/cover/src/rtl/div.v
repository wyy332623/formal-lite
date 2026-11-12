// Local radix-2 restoring divider: one quotient bit per clock, 32 iterations.
// Signed division truncates toward zero; remainder has the dividend's sign.
module div(
    input wire div_clk,
    input wire resetn,
    input wire cancel,
    input wire div,
    input wire div_signed,
    input wire [31:0] x,
    input wire [31:0] y,
    output reg [31:0] s,
    output reg [31:0] r,
    output reg complete
);
reg busy, quotient_negative, remainder_negative;
reg  [ 5:0] iteration;
reg  [31:0] quotient, remainder, divisor;
wire        x_negative = div_signed && x[31];
wire        y_negative = div_signed && y[31];
wire [31:0] x_abs = x_negative ? (~x + 32'd1) : x;
wire [31:0] y_abs = y_negative ? (~y + 32'd1) : y;
wire        launch = resetn && !cancel && div && !busy && !complete;
// Shift the next dividend bit into the partial remainder, then try subtracting
// the divisor. The extra bit preserves the carry for unsigned 32-bit operands.
wire [32:0] shifted_remainder = {remainder, quotient[31]};
wire [32:0] trial_remainder = shifted_remainder - {1'b0, divisor};
wire        quotient_bit = !trial_remainder[32];
wire [31:0] next_remainder = quotient_bit ? trial_remainder[31:0]
                                          : shifted_remainder[31:0];
wire [31:0] next_quotient = {quotient[30:0], quotient_bit};
always @(posedge div_clk) begin
    if (!resetn) begin
        busy <= 1'b0;
        complete <= 1'b0;
        s <= 32'b0;
        r <= 32'b0;
        quotient_negative  <= 1'b0;
        remainder_negative <= 1'b0;
        iteration <= 6'd0;
        quotient  <= 32'b0;
        remainder <= 32'b0;
        divisor   <= 32'b0;
    end else if (cancel) begin
        // Cancel has priority even on the last iteration; no stale completion.
        busy <= 1'b0;
        complete <= 1'b0;
    end else begin
        // Retain completion/result while EX is blocked by its next stage.
        if (!div) complete <= 1'b0;
        if (launch) begin
            busy <= 1'b1;
            complete  <= 1'b0;
            iteration <= 6'd0;
            quotient  <= x_abs;
            remainder <= 32'b0;
            divisor   <= y_abs;
            // Division by zero returns all-one quotient and original dividend.
            quotient_negative  <= (x_negative ^ y_negative) && (y != 32'b0);
            remainder_negative <=  x_negative;
        end else if (busy) begin
            quotient  <= next_quotient;
            remainder <= next_remainder;
            if (iteration == 6'd31) begin
                busy <= 1'b0;
                complete <= 1'b1;
                s <= quotient_negative  ? (~next_quotient  + 32'd1) : next_quotient;
                r <= remainder_negative ? (~next_remainder + 32'd1) : next_remainder;
            end else iteration <= iteration + 6'd1;
        end
    end
end
endmodule
