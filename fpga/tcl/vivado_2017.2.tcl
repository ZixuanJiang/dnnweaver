#------------------------------------------------------------------------
# reportCriticalPaths
#------------------------------------------------------------------------
# This function generates a CSV file that provides a summary of the first
# 50 violations for both Setup and Hold analysis. So a maximum number of
# 100 paths are reported.
#------------------------------------------------------------------------
proc reportCriticalPaths { fileName } {
# Open the specified output file in write mode
    set FH [open $fileName w]
    # Write the current date and CSV format to a file header
    puts $FH "#\n# File created on [clock format [clock seconds]]\n#\n"
    puts $FH "Startpoint,Endpoint,DelayType,Slack,#Levels,#LUTs"
    # Iterate through both Min and Max delay types
    foreach delayType {max min} {
    # Collect details from the 50 worst timing paths for the current analysis
    # (max = setup/recovery, min = hold/removal)
    # The $path variable contains a Timing Path object.
        foreach path [get_timing_paths -delay_type $delayType -max_paths 50 -nworst 1] {
        # Get the LUT cells of the timing paths
        set luts [get_cells -filter {REF_NAME =~ LUT*} -of_object $path]

        # Get the startpoint of the Timing Path object
        set startpoint [get_property STARTPOINT_PIN $path]
        # Get the endpoint of the Timing Path object
        set endpoint [get_property ENDPOINT_PIN $path]
        # Get the slack on the Timing Path object
        set slack [get_property SLACK $path]
        # Get the number of logic levels between startpoint and endpoint
        set levels [get_property LOGIC_LEVELS $path]
        # Save the collected path details to the CSV file
        puts $FH "$startpoint,$endpoint,$delayType,$slack,$levels,[llength $luts]"
        }
    }
    # Close the output file
    close $FH
    puts "CSV file $fileName has been created.\n"
    return 0
}; # End PROC
#------------------------------------------------------------------------

# Set the reference directory for source file relative paths (by default the value is script directory path)
puts "DnnWeaver: Creating Project"
set_param messaging.defaultLimit 10000
set origin_dir "."

set top_module [lindex $argv 0]
puts "DnnWeaver: Top module is : $top_module"

set frequency [lindex $argv 1]
puts "DnnWeaver: Frequency is : $frequency MHz"

set hw_dir [lindex $argv 2]
puts "DnnWeaver: Verilog Path is : $hw_dir"

set file_list [split [exec cat $origin_dir/$hw_dir/file.list | egrep -v "\#" | egrep -v "^\s*$" | egrep -v "testbench" | awk {{print "hardware/"$0}}] "\n"]
set files [split [string trim $file_list]]
#puts $files

# Set the directory path for the original project from where this script was exported
set orig_proj_dir "[file normalize "$origin_dir/"]"

# Create project
create_project dnnweaver ./vivado -force

# Set the directory path for the new project
set proj_dir [get_property directory [current_project]]

# Set project properties
set obj [get_projects dnnweaver]
set_property "part" "xc7z020clg484-1" $obj
set_property "board_part" "xilinx.com:zc702:part0:1.2" $obj
set_property "default_lib" "xil_defaultlib" $obj
set_property "simulator_language" "Mixed" $obj

# Create 'sources_1' fileset (if not found)
if {[string equal [get_filesets -quiet sources_1] ""]} {
  create_fileset -srcset sources_1
}

# Generate ZYNQ block
puts "DnnWeaver: Generating Zynq block"
global argv
source tcl/zynq_1AXIHP0_1AXIGP0_2017.2.tcl
puts "DnnWeaver: Generating Zynq block - done"

# Set 'sources_1' fileset object
set obj [get_filesets sources_1]


add_files -norecurse -fileset $obj $files

# Set 'sources_1' fileset file properties for local files
set file "zc702/zc702.bd"
set file_obj [get_files -of_objects [get_filesets sources_1] [list "*$file"]]
if { ![get_property "is_locked" $file_obj] } {
    set_property "generate_synth_checkpoint" "0" $file_obj
}

generate_target all [get_files  $origin_dir/vivado/dnnweaver.srcs/sources_1/bd/zc702/zc702.bd]
update_compile_order -fileset sources_1

# Set 'sources_1' fileset properties
set obj [get_filesets sources_1]
set_property "top" $top_module $obj

# Create 'sources_1' fileset (if not found)
if {[string equal [get_filesets -quiet sources_1] ""]} {
  create_fileset -srcset sources_1
}

# Create 'constrs_1' fileset (if not found)
if {[string equal [get_filesets -quiet constrs_1] ""]} {
  create_fileset -constrset constrs_1
}

# Set 'constrs_1' fileset object
set obj [get_filesets constrs_1]

# Empty (no sources present)

# Set 'constrs_1' fileset properties
set obj [get_filesets constrs_1]

# Create 'sim_1' fileset (if not found)
if {[string equal [get_filesets -quiet sim_1] ""]} {
  create_fileset -simset sim_1
}

# Set 'sim_1' fileset object
set obj [get_filesets sim_1]
# Empty (no sources present)

# Set 'sim_1' fileset properties
set obj [get_filesets sim_1]
set_property "top" $top_module $obj
set_property top $top_module [current_fileset]
update_compile_order -fileset sources_1
set_property "transport_int_delay" "0" $obj
set_property "transport_path_delay" "0" $obj
set_property "xelab.nosort" "1" $obj
set_property "xelab.unifast" "" $obj

# Create 'synth_1' run (if not found)
if {[string equal [get_runs -quiet synth_1] ""]} {
  create_run -name synth_1 -part xc7z020clg484-1 -flow {Vivado Synthesis 2016} -strategy "Flow_PerfOptimized_high" -constrset constrs_1
} else {
  set_property strategy "Flow_PerfOptimized_high" [get_runs synth_1]
  set_property flow "Vivado Synthesis 2016" [get_runs synth_1]
}
set obj [get_runs synth_1]
set_property "constrset" "constrs_1" $obj
set_property "description" "Higher performance designs, resource sharing is turned off, the global fanout guide is set to a lower number, FSM extraction forced to one-hot, LUT combining is disabled, equivalent registers are preserved, SRL are inferred  with a larger threshold" $obj
set_property "flow" "Vivado Synthesis 2016" $obj
set_property "name" "synth_1" $obj
set_property "needs_refresh" "0" $obj
# set_property "pr_configuration" "" $obj
set_property "srcset" "sources_1" $obj
set_property "strategy" "Flow_PerfOptimized_high" $obj
set_property "incremental_checkpoint" "" $obj
set_property "include_in_archive" "1" $obj
set_property "steps.synth_design.tcl.pre" "" $obj
set_property "steps.synth_design.tcl.post" "" $obj
set_property "steps.synth_design.args.flatten_hierarchy" "rebuilt" $obj
set_property "steps.synth_design.args.gated_clock_conversion" "off" $obj
set_property "steps.synth_design.args.bufg" "12" $obj
set_property "steps.synth_design.args.fanout_limit" "400" $obj
set_property "steps.synth_design.args.directive" "Default" $obj
set_property "steps.synth_design.args.retiming" "0" $obj
set_property "steps.synth_design.args.fsm_extraction" "one_hot" $obj
set_property "steps.synth_design.args.keep_equivalent_registers" "1" $obj
set_property "steps.synth_design.args.resource_sharing" "off" $obj
set_property "steps.synth_design.args.control_set_opt_threshold" "auto" $obj
set_property "steps.synth_design.args.no_lc" "1" $obj
set_property "steps.synth_design.args.no_srlextract" "0" $obj
set_property "steps.synth_design.args.shreg_min_size" "5" $obj
set_property "steps.synth_design.args.max_bram" "-1" $obj
set_property "steps.synth_design.args.max_uram" "-1" $obj
set_property "steps.synth_design.args.max_dsp" "-1" $obj
set_property "steps.synth_design.args.max_bram_cascade_height" "-1" $obj
set_property "steps.synth_design.args.max_uram_cascade_height" "-1" $obj
set_property "steps.synth_design.args.cascade_dsp" "auto" $obj
set_property "steps.synth_design.args.assert" "0" $obj
set_property -name {steps.synth_design.args.more options} -value {} -objects $obj

# set the current synth run
current_run -synthesis [get_runs synth_1]

# Create 'impl_1' run (if not found)
if {[string equal [get_runs -quiet impl_1] ""]} {
  create_run -name impl_1 -part xc7z020clg484-1 -flow {Vivado Implementation 2016} -strategy "Performance_Retiming" -constrset constrs_1 -parent_run synth_1
} else {
  set_property strategy "Performance_Retiming" [get_runs impl_1]
  set_property flow "Vivado Implementation 2016" [get_runs impl_1]
}
set obj [get_runs impl_1]
set_property "constrset" "constrs_1" $obj
set_property "description" "Combines retiming in phys_opt_design with extra placement optimization and higher router delay cost." $obj
set_property "flow" "Vivado Implementation 2016" $obj
set_property "name" "impl_1" $obj
set_property "needs_refresh" "0" $obj
set_property "pr_configuration" "" $obj
set_property "srcset" "sources_1" $obj
set_property "strategy" "Performance_Retiming" $obj
set_property "incremental_checkpoint" "" $obj
set_property "include_in_archive" "1" $obj
set_property "steps.opt_design.is_enabled" "1" $obj
set_property "steps.opt_design.tcl.pre" "" $obj
set_property "steps.opt_design.tcl.post" "" $obj
set_property "steps.opt_design.args.verbose" "0" $obj
set_property "steps.opt_design.args.directive" "Default" $obj
set_property -name {steps.opt_design.args.more options} -value {} -objects $obj
set_property "steps.power_opt_design.is_enabled" "0" $obj
set_property "steps.power_opt_design.tcl.pre" "" $obj
set_property "steps.power_opt_design.tcl.post" "" $obj
set_property -name {steps.power_opt_design.args.more options} -value {} -objects $obj
set_property "steps.place_design.tcl.pre" "" $obj
set_property "steps.place_design.tcl.post" "" $obj
set_property "steps.place_design.args.directive" "ExtraPostPlacementOpt" $obj
set_property -name {steps.place_design.args.more options} -value {} -objects $obj
set_property "steps.post_place_power_opt_design.is_enabled" "0" $obj
set_property "steps.post_place_power_opt_design.tcl.pre" "" $obj
set_property "steps.post_place_power_opt_design.tcl.post" "" $obj
set_property -name {steps.post_place_power_opt_design.args.more options} -value {} -objects $obj
set_property "steps.phys_opt_design.is_enabled" "1" $obj
set_property "steps.phys_opt_design.tcl.pre" "" $obj
set_property "steps.phys_opt_design.tcl.post" "" $obj
set_property "steps.phys_opt_design.args.directive" "AlternateFlowWithRetiming" $obj
set_property -name {steps.phys_opt_design.args.more options} -value {} -objects $obj
set_property "steps.route_design.tcl.pre" "" $obj
set_property "steps.route_design.tcl.post" "" $obj
set_property "steps.route_design.args.directive" "Explore" $obj
set_property -name {steps.route_design.args.more options} -value {} -objects $obj
set_property "steps.post_route_phys_opt_design.is_enabled" "0" $obj
set_property "steps.post_route_phys_opt_design.tcl.pre" "" $obj
set_property "steps.post_route_phys_opt_design.tcl.post" "" $obj
set_property "steps.post_route_phys_opt_design.args.directive" "Default" $obj
set_property -name {steps.post_route_phys_opt_design.args.more options} -value {} -objects $obj
set_property "steps.write_bitstream.tcl.pre" "" $obj
set_property "steps.write_bitstream.tcl.post" "" $obj
set_property "steps.write_bitstream.args.raw_bitfile" "0" $obj
set_property "steps.write_bitstream.args.mask_file" "0" $obj
set_property "steps.write_bitstream.args.no_binary_bitfile" "0" $obj
set_property "steps.write_bitstream.args.bin_file" "0" $obj
set_property "steps.write_bitstream.args.readback_file" "0" $obj
set_property "steps.write_bitstream.args.logic_location_file" "0" $obj
set_property "steps.write_bitstream.args.verbose" "0" $obj
set_property -name {steps.write_bitstream.args.more options} -value {} -objects $obj

# set the current impl run
current_run -implementation [get_runs impl_1]

set outputDir ./synthesis-output
file mkdir $outputDir

puts "DnnWeaver: Running Synthesis"
synth_design -top $top_module -part xc7z020clg484-1
write_checkpoint -force $outputDir/post_synth.dcp
report_timing_summary -file $outputDir/post_synth_timing_summary.rpt -max_paths 1000
report_utilization -file $outputDir/post_synth_util.rpt
reportCriticalPaths $outputDir/post_synth_critpath_report.csv
#
# STEP#2: run logic optimization, placement and physical logic optimization,
# write design checkpoint, report utilization and timing estimates
#

puts "DnnWeaver: Generating utilization report"
report_utilization -hierarchical -file $outputDir/utilization_post_synth.rpt

opt_design
reportCriticalPaths $outputDir/post_opt_critpath_report.csv
puts "DnnWeaver: Running Placement"
place_design
report_clock_utilization -file $outputDir/clock_util.rpt
puts "DnnWeaver: Checking for Timing violations after placement"
#
# Optionally run optimization if there are timing violations after placement
if {[get_property SLACK [get_timing_paths -max_paths 1 -nworst 1 -setup]] < 0} {
    puts "DnnWeaver: Timing violations found, Running Physical Optimization"
    puts "Found setup timing violations => running physical optimization"
    phys_opt_design
} else {
    puts "DnnWeaver: No timing violations found"
}

###   if {[get_property SLACK [get_timing_paths -max_paths 1 -nworst 1 -setup]] < 0}
###   {
 ###   puts “Found setup timing violations => running physical optimization”
 ###   phys_opt_design
###   }
write_checkpoint -force $outputDir/post_place.dcp
report_utilization -file $outputDir/post_place_util.rpt
report_timing_summary -file $outputDir/post_place_timing_summary.rpt -max_paths 1000
#
# STEP#3: run the router, write the post-route design checkpoint, report the routing
# status, report timing, power, and DRC, and finally save the Verilog netlist.
#
puts "DnnWeaver: Running Routing"
route_design
write_checkpoint -force $outputDir/post_route.dcp
report_route_status -file $outputDir/post_route_status.rpt
report_timing_summary -file $outputDir/post_route_timing_summary.rpt -max_paths 1000
report_power -file $outputDir/post_route_power.rpt
report_drc -file $outputDir/post_imp_drc.rpt
write_verilog -force $outputDir/cpu_impl_netlist.v -mode timesim -sdf_anno true
reportCriticalPaths $outputDir/post_route_critpath_report.csv
#
# STEP#4: generate a bitstream
#
if {[get_property SLACK [get_timing_paths -max_paths 1 -nworst 1 -setup]] < 0} {
    puts "DnnWeaver: Timing violations found after routing"
}

puts "DnnWeaver: Generating Bitfile $outputDir/$top_module"
write_bitstream -force $outputDir/$top_module.bit

puts "DnnWeaver: Generating HDF"
write_hwdef -force -file $outputDir/$top_module.hdf

puts "DnnWeaver: Generating utilization report"
report_utilization -hierarchical -file $outputDir/utilization_post_route.rpt

puts "DnnWeaver: Done!"
