`timescale 1ns/1ps
module register #(
    parameter NUM_STAGES = 1,
    parameter DATA_WIDTH = 1
)(
    input  wire                  CLK,
    input  wire                  RESET,
    input  wire [DATA_WIDTH-1:0] DIN,
    output wire [DATA_WIDTH-1:0] DOUT
);

genvar i;
generate
if (NUM_STAGES == 0) 
begin
    assign DOUT = DIN;
end 
else if (NUM_STAGES > 0) 
begin
    reg [NUM_STAGES*DATA_WIDTH-1:0] din_delay;
    always @(posedge CLK)
    begin
        if(RESET)
        begin
            din_delay[DATA_WIDTH-1:0] <= 0;
        end else
        begin
            din_delay[DATA_WIDTH-1:0] <= DIN;
        end
    end
    for (i=1; i<NUM_STAGES; i=i+1) 
	 begin : REGISTER_STAGES
        always @(posedge CLK)
        begin
            if(RESET)
            begin
                din_delay[i*DATA_WIDTH+:DATA_WIDTH] <= 0;
            end else
            begin
                din_delay[i*DATA_WIDTH+:DATA_WIDTH] <= din_delay[(i-1)*DATA_WIDTH+:DATA_WIDTH];
            end
        end
    end
    assign DOUT = din_delay[(NUM_STAGES-1)*DATA_WIDTH+:DATA_WIDTH];
end
endgenerate


endmodule
