`include "common.vh"
module data_width_converter #(
// ******************************************************************
// Parameters
// ******************************************************************
  parameter integer IN_WIDTH                = 64,
  parameter integer OUT_WIDTH               = 112,
  parameter integer OP_WIDTH                = 16
)
(
// ******************************************************************
// IO
// ******************************************************************
  input  wire                               clk,
  input  wire                               reset,
  input  wire                               s_write_req,
  output wire                               s_write_ready,
  input  wire  [ IN_WIDTH     -1 : 0 ]      s_write_data,
  output wire                               m_write_req,
  input  wire                               m_write_ready,
  output wire  [ OUT_WIDTH    -1 : 0 ]      m_write_data
);


genvar g;
generate
  if (OUT_WIDTH == IN_WIDTH)
  begin
    assign m_write_data = s_write_data;
    assign m_write_req = s_write_req;
    assign s_write_ready = m_write_ready;
  end
  else begin

    localparam integer MAX_DCOUNT = (OUT_WIDTH + IN_WIDTH) / OP_WIDTH - 1;
    localparam integer DATA_COUNT_W = `C_LOG_2(MAX_DCOUNT+1);
    localparam integer IN_NUM_DATA = IN_WIDTH / OP_WIDTH;
    localparam integer OUT_NUM_DATA = OUT_WIDTH / OP_WIDTH;

    localparam integer DREG_W = OUT_WIDTH + IN_WIDTH - OP_WIDTH;

    reg [ DATA_COUNT_W    : 0 ] dcount;
    reg [ DATA_COUNT_W    : 0 ] next_dcount;

    reg [ DREG_W       -1 : 0 ] wr_data;
    reg [ DREG_W       -1 : 0 ] next_wr_data;

    reg [ DATA_COUNT_W -1 : 0 ] rshift;
    reg [ DATA_COUNT_W -1 : 0 ] next_rshift;

    always @(*)
    begin: PACK_FSM
      next_dcount = dcount;
      next_rshift = rshift;
      case (m_write_req)
        0: begin
          if (s_write_req && s_write_ready)
          begin
            next_dcount = dcount + IN_NUM_DATA;
            next_rshift = rshift - IN_NUM_DATA;
          end
        end
        1: begin
          if (s_write_req && s_write_ready) begin
            next_dcount = dcount + IN_NUM_DATA - OUT_NUM_DATA;
            next_rshift = rshift - IN_NUM_DATA + OUT_NUM_DATA;
          end
          else begin
            next_dcount = dcount - OUT_NUM_DATA;
            next_rshift = rshift + OUT_NUM_DATA;
          end

        end
      endcase
    end

    always @(posedge clk)
    begin
      if (reset)
        wr_data <= 0;
      else if (s_write_ready && s_write_req)
        wr_data <= {s_write_data, wr_data} >> IN_WIDTH;
    end

    always @(posedge clk)
    begin
      if (reset)
        dcount <= 0;
      else
        dcount <= next_dcount;
    end

    always @(posedge clk)
    begin
      if (reset)
        rshift <= MAX_DCOUNT;
      else
        rshift <= next_rshift;
    end

    assign m_write_req = dcount >= OUT_NUM_DATA;
    assign m_write_data = wr_data >> (rshift * OP_WIDTH);
    assign s_write_ready = (dcount <= 2*OUT_NUM_DATA - 1);

  end
endgenerate

`ifdef TOPLEVEL_data_packer
  initial
  begin
    $dumpfile("data_packer.vcd");
    $dumpvars(0,data_packer);
  end
`endif

endmodule
