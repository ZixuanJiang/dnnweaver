CONFIG_FILE := Makefile.config
include $(CONFIG_FILE)

NUM_PE ?= 8
NUM_PU ?= 1
FPGA ?= zynq


DW_COMPILER := ../compiler/compiler.py
PU_INSTRUCTIONS := hardware/include/pu_controller_bin.vh
MEM_RD_INSTRUCTIONS := hardware/include/rd_mem_controller.vh
MEM_WR_INSTRUCTIONS := hardware/include/wr_mem_controller.vh
DW_COMPILER_OUTPUT := $(PU_INSTRUCTIONS) $(MEM_RD_INSTRUCTIONS) $(MEM_WR_INSTRUCTIONS)
DW_COMPILER_DEPS := ../compiler/DWlayer.py

PROTOTXT:= ../compiler/sample_prototxts/lenet.prototxt
#PROTOTXT:= ../compiler/sample_prototxts/loopback.prototxt
#PROTOTXT:= ../compiler/sample_prototxts/vgg_16.prototxt
#PROTOTXT:= ../compiler/sample_prototxts/cifar10_full.prototxt

HW_SRC_DIR := hardware
HW_FILELIST := $(HW_SRC_DIR)/file.list
HW_SRC_FILES := $(shell cat $(HW_FILELIST) | egrep -v '\#' | grep -v "include")
HW_SRC := $(HW_SRC_FILES:%=$(HW_SRC_DIR)/%)

SIM_COMPILER := iverilog
SIM_INCLUDE_DIR := $(HW_SRC_DIR)/include
SIM_COMPILER_FLAGS := -I $(SIM_INCLUDE_DIR) -g2012 -Dsimulation
SIM_BINDIR = $(HW_SRC_DIR)/bin
SIM_WAVEFORM_DIR := $(SIM_BINDIR)/waveform

SIM_TBLIST := testbench/tb.list
SIM_TESTS := $(shell cat $(HW_SRC_DIR)/$(SIM_TBLIST) | egrep -v '\#')

TOP_MODULE ?= zynq_wrapper
#TOP_MODULE ?= zynq_wrapper
FREQUENCY ?= 150

OUTPUT_FOLDER := synthesis-output
LOGFILE := vivado.log
BITFILE := $(OUTPUT_FOLDER)/$(TOP_MODULE).bit
BITFILE_GOLDEN := $(OUTPUT_FOLDER)/$(TOP_MODULE)_golden.bit

SW_DIR := ./arm_software
CFLAGS := -O3 -I $(SW_DIR)/lib -c
SW_SRCDIR := $(SW_DIR)/src
SW_LIBDIR := $(SW_DIR)/lib
SW_BINDIR := $(OUTPUT_FOLDER)

STANDALONE_LDFLAGS := -Wl,-T -Wl,$(SW_DIR)/lib/lscript.ld -L $(SW_DIR)/lib
STANDALONE_LIBS := -Wl,--start-group,-lxil,-lgcc,-lc,-lm,--end-group
SW_STANDALONE_OBJDIR := $(SW_DIR)/obj/standalone
SW_STANDALONE_SRCFILES := $(SW_SRCDIR)/standalone.c $(SW_SRCDIR)/platform.c
SW_STANDALONE_OBJS := $(SW_STANDALONE_SRCFILES:$(SW_SRCDIR)/%.c=$(SW_STANDALONE_OBJDIR)/%.o)
STANDALONE := $(SW_BINDIR)/standalone.elf

LINUX_LDFLAGS := 
SW_LINUX_OBJDIR := $(SW_DIR)/obj/linux
SW_LINUX_SRCFILES := $(SW_SRCDIR)/linux.c $(SW_SRCDIR)/accelerator.c
SW_LINUX_SRC_OBJS := $(SW_LINUX_SRCFILES:$(SW_SRCDIR)/%.c=$(SW_LINUX_OBJDIR)/%.o)
LINUX := $(SW_BINDIR)/linux.elf

VIVADO_FLAGS := -notrace
VIVADO_TCL:=tcl/vivado_$(VIVADO_VERSION).tcl

XMD_TCL:=tcl/run_benchmark.tcl
RESET_ZYNQ_TCL:=tcl/reset_zynq.tcl
PS7_TCL:=tcl/ps7_init.tcl
###############################################################################
all: $(BITFILE) ELF

###############################################################################
############ SIMULATION ############
test: $(SIM_TESTS) $(DW_COMPILER_OUTPUT)
	@echo $(SIM_TESTS)

$(SIM_TESTS:%=$(SIM_BINDIR)/%.out): $(HW_FILELIST) $(HW_SRC) $(DW_COMPILER_OUTPUT)
	@echo "Compiling Testbench - $@"
	@mkdir -p $(SIM_BINDIR)
	@$(SIM_COMPILER) $(SIM_COMPILER_FLAGS) -o $@ -s $(@:$(SIM_BINDIR)/%.out=%)_tb $(HW_SRC)
	@echo 'Done !'
	@echo

$(SIM_TESTS): %:$(SIM_BINDIR)/%.out $(DW_COMPILER_OUTPUT)
	@echo $(SIM_BINDIR)
	@echo "Simulating Testbench $<"
	@mkdir -p $(SIM_WAVEFORM_DIR)
	@$(SIMULATOR) $(SIMULATOR_FLAGS) $<
	@echo $(SIMULATOR)
	@mkdir -p $(SIM_BINDIR)
	#vcd2fst -v $@_tb.vcd -f $(SIM_WAVEFORM_DIR)/$@_tb.fst -p -F
	mv $@_tb.vcd $(SIM_WAVEFORM_DIR)/$@_tb.vcd
	@echo 'Done !'
	@echo
###############################################################################

###############################################################################
############ SYNTHESIS ############

$(BITFILE): $(HW_SRC) $(HW_FILELIST) $(VIVADO_TCL) $(DW_COMPILER_OUTPUT) $(PROTOTXT)
	@echo "Synthesizing DnnWeaver"
	@\rm -rf $(OUTPUT_FOLDER)
	@mkdir -p $(OUTPUT_FOLDER)
	@$(VIVADO_BIN) -mode batch -nojournal -nolog $(VIVADO_FLAGS) -source $(VIVADO_TCL) -tclargs $(TOP_MODULE) $(FREQUENCY) $(HW_SRC_DIR) 2>&1 | tee $(OUTPUT_FOLDER)/$(LOGFILE) | grep "DnnWeaver"
	@echo "done"

vivado_gui: 
	$(VIVADO) &
###############################################################################

###############################################################################
############ SOFTWARE ############

ELF: $(STANDALONE) $(LINUX)

$(STANDALONE): $(SW_STANDALONE_OBJS)
	@mkdir -p $(OUTPUT_FOLDER)
	@echo -n 'Linking ...'
	@$(STANDALONE_CC) $(STANDALONE_LDFLAGS) $(SW_STANDALONE_OBJS) -o $@ $(STANDALONE_LIBS)
	@echo ' Done !'
	@echo 'Executable generated : ' $@
	@echo ' '

$(SW_STANDALONE_OBJS):$(SW_STANDALONE_OBJDIR)/%.o:$(SW_SRCDIR)/%.c
	@echo -n Compiling $< ...
	mkdir -p $(SW_STANDALONE_OBJDIR)
	@$(STANDALONE_CC) $(CFLAGS) $< -o $@
	@echo ' Done !'

$(LINUX): $(SW_LINUX_SRC_OBJS)
	@mkdir -p $(OUTPUT_FOLDER)
	@echo -n 'Linking ...'
	@echo $(SW_LINUX_SRC_OBJS)
	@$(LINUX_CC) $(LINUX_LDFLAGS) $(SW_LINUX_SRC_OBJS) -o $@ $(LINUX_LIBS)
	@echo ' Done !'
	@echo 'Executable generated : ' $@
	@echo ' '

$(SW_LINUX_SRC_OBJS):$(SW_LINUX_OBJDIR)/%.o:$(SW_SRCDIR)/%.c
	@echo -n Compiling $< ...
	mkdir -p $(SW_LINUX_OBJDIR)
	@$(LINUX_CC) $(CFLAGS) $< -o $@
	@echo ' Done !'
###############################################################################

###############################################################################
############ LAUNCH ############
launch: $(STANDALONE) $(LINUX)
	@echo "Launching DnnWeaver"
	@$(XMD) -tcl $(XMD_TCL) $(BITFILE) $(PS7_TCL) $(STANDALONE) 2>&1 | tee $(OUTPUT_FOLDER)/launch.log | grep -i "error"

launch_golden: 
	$(XMD) -tcl $(XMD_TCL) $(BITFILE_GOLDEN) $(PS7_TCL) $(STANDALONE)

###############################################################################
############ COMPILER ############
$(DW_COMPILER_OUTPUT): $(DW_COMPILER) $(PROTOTXT) $(DW_COMPILER_DEPS)
	@echo "Generating instructions for DnnWeaver"
	@python $(DW_COMPILER) -prototxt $(PROTOTXT) -num_pe $(NUM_PE) -num_pu $(NUM_PU) -b $(SIM_INCLUDE_DIR) -fpga $(FPGA)
	#@python $(DW_COMPILER) -prototxt $(PROTOTXT) -b $(SIM_INCLUDE_DIR) -fpga $(FPGA)

dw_compile: $(DW_COMPILER_OUTPUT)

###############################################################################
############ Cleanup ############
clean:
	@echo Cleaning up...
	@rm -rf $(SW_STANDALONE_OBJDIR)/*.o
	@rm -rf $(SW_LINUX_OBJDIR)/*.o
	@rm -f $(STANDALONE)
	@rm -f $(DW_COMPILER_OUTPUT)
	@rm -rf $(OUTPUT_FOLDER)
	@rm -rf vivado
	@rm -rf vivado.* vivado_*.*
	@rm -rf *.jou *.log *.str
	@rm -rf *.vcd *.gtkw
	@rm -f $(SIM_TESTS:%=$(SIM_BINDIR)/%.out)
	@echo 'Done !'
	@echo
###############################################################################
