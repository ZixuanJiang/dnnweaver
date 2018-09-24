`include "dw_params.vh"
module dnn_accelerator_top #(
  parameter READ_ADDR_BASE_0   = 32'h00000000,
  parameter WRITE_ADDR_BASE_0  = 32'h02000000,
  parameter NUM_PU             = `num_pu,
  parameter ROM_ADDR_W         = 3
)
(
  input  wire clk,
  input  wire reset,
  input  wire start,
  output wire done,
  output wire [ ROM_ADDR_W - 1 : 0 ] wr_cfg_idx,
  output wire [ ROM_ADDR_W - 1 : 0 ] rd_cfg_idx,
  output wire [ 3          - 1 : 0 ] pu_controller_state,
  output wire [ 2          - 1 : 0 ] vecgen_state,
  output reg  [ 16         - 1 : 0 ] vecgen_read_count,
  output wire [ NUM_PU     - 1 : 0 ] outbuf_push,
  output wire [ NUM_PU     - 1 : 0 ] pu_write_valid,
  output wire [ 11         - 1 : 0 ] inbuf_count,
  output wire [ 32         - 1 : 0 ] buffer_read_count,
  output wire [ 32         - 1 : 0 ] stream_read_count
);

  wire [ 31 : 0 ]    axi_araddr;
  wire [ 1  : 0 ]    axi_arburst;
  wire [ 3  : 0 ]    axi_arcache;
  wire [ 5  : 0 ]    axi_arid;
  wire [ 3  : 0 ]    axi_arlen;
  wire [ 1  : 0 ]    axi_arlock;
  wire [ 2  : 0 ]    axi_arprot;
  wire [ 3  : 0 ]    axi_arqos;
  wire               axi_arready;
  wire [ 2  : 0 ]    axi_arsize;
  wire               axi_arvalid;
  wire [ 31 : 0 ]    axi_awaddr;
  wire [ 1  : 0 ]    axi_awburst;
  wire [ 3  : 0 ]    axi_awcache;
  wire [ 5  : 0 ]    axi_awid;
  wire [ 3  : 0 ]    axi_awlen;
  wire [ 1  : 0 ]    axi_awlock;
  wire [ 2  : 0 ]    axi_awprot;
  wire [ 3  : 0 ]    axi_awqos;
  wire               axi_awready;
  wire [ 2  : 0 ]    axi_awsize;
  wire               axi_awvalid;
  wire [ 5  : 0 ]    axi_bid;
  wire               axi_bready;
  wire [ 1  : 0 ]    axi_bresp;
  wire               axi_bvalid;
  wire [ 63 : 0 ]    axi_rdata;
  wire [ 5  : 0 ]    axi_rid;
  wire               axi_rlast;
  wire               axi_rready;
  wire [ 1  : 0 ]    axi_rresp;
  wire               axi_rvalid;
  wire [ 63 : 0 ]    axi_wdata;
  wire [ 5  : 0 ]    axi_wid;
  wire               axi_wlast;
  wire               axi_wready;
  wire [ 7  : 0 ]    axi_wstrb;
  wire               axi_wvalid;

  wire [ 86 - 1 : 0] dnn_accelerator_axi_input;
  wire [204 - 1 : 0] dnn_accelerator_axi_output;

  reg                axi_fake;

  localparam integer NUM_PE             = `num_pe;
  localparam integer ADDR_W             = 32;
  localparam integer DATA_W             = 64;
  localparam integer BASE_ADDR_W        = ADDR_W;
  localparam integer OFFSET_ADDR_W      = ADDR_W;
  localparam integer TX_SIZE_WIDTH      = 20;
  localparam integer RD_LOOP_W          = 32;
  localparam integer D_TYPE_W           = 2;

// ==================================================================
// Dnn Accelerator
// ==================================================================
  dnn_accelerator #(
  // INPUT PARAMETERS
    .NUM_PE                   ( NUM_PE             ),
    .NUM_PU                   ( NUM_PU             ),
    .ADDR_W                   ( ADDR_W             ),
    .AXI_DATA_W               ( DATA_W             ),
    .BASE_ADDR_W              ( BASE_ADDR_W        ),
    .OFFSET_ADDR_W            ( OFFSET_ADDR_W      ),
    .RD_LOOP_W                ( RD_LOOP_W          ),
    .TX_SIZE_WIDTH            ( TX_SIZE_WIDTH      ),
    .D_TYPE_W                 ( D_TYPE_W           ),
    .ROM_ADDR_W               ( ROM_ADDR_W         )
  ) accelerator ( // PORTS
    .clk                      ( clk                ),
    .reset                    ( reset              ),

    .start                    ( start              ),
    .done                     ( done               ),

    .rd_cfg_idx               ( rd_cfg_idx         ),
    .wr_cfg_idx               ( wr_cfg_idx         ),

    .pu_controller_state      ( pu_controller_state),
    .vecgen_state             ( vecgen_state       ),
    .vecgen_read_count        ( vecgen_read_count  ),

    .dbg_kw                   (                    ),
    .dbg_kh                   (                    ),
    .dbg_iw                   (                    ),
    .dbg_ih                   (                    ),
    .dbg_ic                   (                    ),
    .dbg_oc                   (                    ),
    .outbuf_push              ( outbuf_push        ),

    .pu_write_valid           ( pu_write_valid     ),
    .inbuf_count              ( inbuf_count        ),
    .buffer_read_count        ( buffer_read_count  ),
    .stream_read_count        ( stream_read_count  ),

    .M_AXI_AWID               ( axi_awid           ),
    .M_AXI_AWADDR             ( axi_awaddr         ),
    .M_AXI_AWLEN              ( axi_awlen          ),
    .M_AXI_AWSIZE             ( axi_awsize         ),
    .M_AXI_AWBURST            ( axi_awburst        ),
    .M_AXI_AWLOCK             ( axi_awlock         ),
    .M_AXI_AWCACHE            ( axi_awcache        ),
    .M_AXI_AWPROT             ( axi_awprot         ),
    .M_AXI_AWQOS              ( axi_awqos          ),
    .M_AXI_AWVALID            ( axi_awvalid        ),
    .M_AXI_AWREADY            ( axi_awready        ),
    .M_AXI_WID                ( axi_wid            ),
    .M_AXI_WDATA              ( axi_wdata          ),
    .M_AXI_WSTRB              ( axi_wstrb          ),
    .M_AXI_WLAST              ( axi_wlast          ),
    .M_AXI_WVALID             ( axi_wvalid         ),
    .M_AXI_WREADY             ( axi_wready         ),
    .M_AXI_BID                ( axi_bid            ),
    .M_AXI_BRESP              ( axi_bresp          ),
    .M_AXI_BVALID             ( axi_bvalid         ),
    .M_AXI_BREADY             ( axi_bready         ),
    .M_AXI_ARID               ( axi_arid           ),
    .M_AXI_ARADDR             ( axi_araddr         ),
    .M_AXI_ARLEN              ( axi_arlen          ),
    .M_AXI_ARSIZE             ( axi_arsize         ),
    .M_AXI_ARBURST            ( axi_arburst        ),
    .M_AXI_ARLOCK             ( axi_arlock         ),
    .M_AXI_ARCACHE            ( axi_arcache        ),
    .M_AXI_ARPROT             ( axi_arprot         ),
    .M_AXI_ARQOS              ( axi_arqos          ),
    .M_AXI_ARVALID            ( axi_arvalid        ),
    .M_AXI_ARREADY            ( axi_arready        ),
    .M_AXI_RID                ( axi_rid            ),
    .M_AXI_RDATA              ( axi_rdata          ),
    .M_AXI_RRESP              ( axi_rresp          ),
    .M_AXI_RLAST              ( axi_rlast          ),
    .M_AXI_RVALID             ( axi_rvalid         ),
    .M_AXI_RREADY             ( axi_rready         )
  );
// ==================================================================

// ==================================================================
// We here make AXI interfaces as internal
// To do so, we fake some logics to connect them
// ==================================================================
  assign dnn_accelerator_axi_input = {axi_awready,
                                      axi_wready,
                                      axi_bid,
                                      axi_bresp,
                                      axi_bvalid,
                                      axi_arready,
                                      axi_rid,
                                      axi_rdata,
                                      axi_rresp,
                                      axi_rlast,
                                      axi_rvalid};

  assign dnn_accelerator_axi_output = {axi_awid,
                                       axi_awaddr,
                                       axi_awlen,
                                       axi_awsize,
                                       axi_awburst,
                                       axi_awlock,
                                       axi_awcache,
                                       axi_awprot,
                                       axi_awqos,
                                       axi_awvalid,
                                       axi_wid,
                                       axi_wdata,
                                       axi_wstrb,
                                       axi_wlast,
                                       axi_wvalid,
                                       axi_bready,
                                       axi_arid,
                                       axi_araddr,
                                       axi_arlen,
                                       axi_arsize,
                                       axi_arburst,
                                       axi_arlock,
                                       axi_arcache,
                                       axi_arprot,
                                       axi_arqos,
                                       axi_arvalid,
                                       axi_rready};

  always @(posedge clk) begin
    if (reset) begin
      axi_fake <= 0;
    end else begin
      axi_fake <= ^dnn_accelerator_axi_output;
    end
  end

  genvar i;
  for (i = 0; i < 86; i = i + 1) begin
    assign dnn_accelerator_axi_input[i] = axi_fake;
  end

endmodule
