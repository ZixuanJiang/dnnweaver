`timescale 1ns/1ps
module counter #(
    // INPUT PARAMETERS
    parameter COUNT_WIDTH               = 3
)
(
    // PORTS
    input  wire                         CLK,
    input  wire                         RESET,

    input  wire                         CLEAR,
    input  wire [COUNT_WIDTH-1    : 0]  DEFAULT,

    input  wire                         INC,
    input  wire                         DEC,

    input  wire [COUNT_WIDTH-1    : 0]  MIN_COUNT,
    input  wire [COUNT_WIDTH-1    : 0]  MAX_COUNT,

    output wire                         OVERFLOW,
    output wire                         UNDERFLOW,
    output reg  [COUNT_WIDTH-1    : 0]  COUNT
);

// ******************************************************************
// CONTROL LOGIC
// ******************************************************************

    assign OVERFLOW = (COUNT == MAX_COUNT);
    assign UNDERFLOW = (COUNT == MIN_COUNT);

    // UPCOUNTER
    always @ (posedge CLK)
    begin : COUNTER
        if (RESET)
            COUNT <= 0;
        else if (CLEAR)
            COUNT <= DEFAULT;
        else if (INC && !DEC) begin
            if (!OVERFLOW)
                COUNT <= COUNT + 1'b1;
            else if (OVERFLOW)
                COUNT <= MIN_COUNT;
        end
        else if (DEC && !INC) begin
            if (!UNDERFLOW)
                COUNT <= COUNT - 1'b1;
            else if (UNDERFLOW)
                COUNT <= MAX_COUNT;
        end
    end
endmodule
