VIVADO_EXE := vivado
VIVADO_TCL := tcl/vivado_2017.3.tcl
OUTPUT_FOLDER := impl-output
LOGFILE := vivado.log

TOP_MODULE := dnn_accelerator_top

all:
	$(error Please specify a target)

compile:
	@rm -rf $(OUTPUT_FOLDER)
	@mkdir -p $(OUTPUT_FOLDER)
	@$(VIVADO_EXE) -mode batch -notrace -nolog -nojournal -source $(VIVADO_TCL) -tclargs $(TOP_MODULE) 2>&1 | tee $(OUTPUT_FOLDER)/$(LOGFILE)
	@echo "Done"

open_post_synth:
	@$(VIVADO_EXE) ./impl-output/post_synth.dcp &

open_post_place:
	@$(VIVADO_EXE) ./impl-output/post_place.dcp &

open_post_route:
	@$(VIVADO_EXE) ./impl-output/post_route.dcp &
