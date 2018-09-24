`timescale 1ns/1ps
module fifo_fwft 
// ******************************************************************
// Parameters
// ******************************************************************
#(
    parameter           INIT                = "init.mif",
    parameter integer   DATA_WIDTH          = 4,
    parameter integer   ADDR_WIDTH          = 8,
    parameter integer   RAM_DEPTH           = (1 << ADDR_WIDTH),
    parameter           INITIALIZE_FIFO     = "no"
)
// ******************************************************************
// Port Declarations
// ******************************************************************
(
    input  wire                             clk,
    //input  wire                             pop_enable,
    input  wire                             reset,
    input  wire                             push,
    input  wire                             pop,
    input  wire [DATA_WIDTH-1:0]            data_in,
    output      [DATA_WIDTH-1:0]            data_out,
    output                                  empty,
    output                                  full,
    output      [ADDR_WIDTH:0]              fifo_count
    //debug
    //output                                  fifo_pop,
    //output                                  fifo_empty,
    //output                                  dout_valid
);    
 
// ******************************************************************
// Internal variables
// ******************************************************************
    wire                             fifo_pop;
    wire                             fifo_empty;
    reg                              dout_valid;
    
// ******************************************************************
// Logic
// ******************************************************************
    assign fifo_pop    = !fifo_empty && (!dout_valid || pop);
    //assign fifo_pop    = !fifo_empty && (pop);
    //assign fifo_pop    = !fifo_empty && pop_enable && pop;
    assign empty        = !dout_valid;

    always @ (posedge clk)
    begin
        if (reset) begin
            dout_valid <= 0;
        end
        else if (fifo_pop) begin
            dout_valid <= 1;
        end
        else if (pop) begin
            dout_valid <= 0;
        end
    end
// ******************************************************************
// INSTANTIATIONS
// ******************************************************************

//-----------------------------------
// FIFO
//-----------------------------------
fifo #(
        .DATA_WIDTH         ( DATA_WIDTH   ),
        .ADDR_WIDTH         ( ADDR_WIDTH   ),
        .INIT               ( "init_x.mif" ),
        .INITIALIZE_FIFO    ( "no"         ))

    fifo_buffer(
        .clk                ( clk           ),  //input
        .reset              ( reset         ),  //input
        .push               ( push          ),  //input
        .pop                ( fifo_pop      ),  //input
        .data_in            ( data_in       ),  //input
        .data_out           ( data_out      ),  //output
        .empty              ( fifo_empty    ),  //output
        .full               ( full          ),  //output
        .fifo_count         ( fifo_count    )   //output
);   

endmodule
