# Default settings
set origin_dir "."
source $origin_dir/tcl/common.tcl

set part xcvu095-ffvc1517-3-e
puts "Target Part is : $part"
set project_name dnn
puts "Project name is : $project_name"

# Set the reference directory for source file relative paths (by default the value is script directory path)
puts "Creating Project"
set_param messaging.defaultLimit 10000

set top_module [lindex $argv 0]
puts "Top module is : $top_module"

set file_list [split [exec cat $origin_dir/verilog/file.list | egrep -v "\#" | egrep -v "^\s*$" | egrep -v "testbench"] "\n"]
set raw_files [split [string trim $file_list]]
set files {}
foreach f $raw_files {
  lappend files $origin_dir/verilog/$f
}
puts $files

# Create project
create_project $project_name ./vivado -force

# Set the directory path for the new project
set proj_dir [get_property directory [current_project]]

# Set project properties
set obj [get_projects $project_name]
set_property "part" $part $obj
set_property "default_lib" "xil_defaultlib" $obj

# Create 'sources_1' fileset (if not found)
if {[string equal [get_filesets -quiet sources_1] ""]} {
  create_fileset -srcset sources_1
}

# Set 'sources_1' fileset object
set obj [get_filesets sources_1]
add_files -norecurse -fileset $obj $files
update_compile_order -fileset sources_1

# Set 'sources_1' fileset properties
set obj [get_filesets sources_1]
set_property "top" $top_module $obj

# Create/set 'constrs_1' fileset
if {[string equal [get_filesets -quiet constrs_1] ""]} {
  create_fileset -constrset constrs_1
}
set obj [get_filesets constrs_1]
add_files -norecurse -fileset $obj $origin_dir/xdc/clock_constraints.xdc

# Create 'synth_1' run (if not found)
if {[string equal [get_runs -quiet synth_1] ""]} {
  create_run -name synth_1 -part $part -flow {Vivado Synthesis 2017} -constrset constrs_1
} else {
  set_property flow "Vivado Synthesis 2017" [get_runs synth_1]
}

# set the current synth run
current_run -synthesis [get_runs synth_1]

# Create 'impl_1' run (if not found)
if {[string equal [get_runs -quiet impl_1] ""]} {
  create_run -name impl_1 -part $part -flow {Vivado Implementation 2017} -constrset constrs_1 -parent_run synth_1
} else {
  set_property flow "Vivado Implementation 2017" [get_runs impl_1]
}
set obj [get_runs impl_1]

# set the current impl run
current_run -implementation [get_runs impl_1]


##################
#                #
#  Start the Run #
#                #
##################

set outputDir ./impl-output
file mkdir $outputDir

puts "Running Synthesis"
synth_design -top $top_module -part $part 
write_checkpoint -force $outputDir/post_synth.dcp
report_timing_summary -file $outputDir/post_synth_timing_summary.rpt -max_paths 1000
report_utilization -file $outputDir/post_synth_util.rpt
report_utilization -hierarchical -file $outputDir/post_synth_util_hier.rpt
reportCriticalPaths $outputDir/post_synth_critpath_report.csv

puts "Running Optimization"
opt_design
reportCriticalPaths $outputDir/post_opt_critpath_report.csv

puts "Running Placement"
place_design
report_clock_utilization -file $outputDir/clock_util.rpt
puts "DnnWeaver: Checking for Timing violations after placement"

write_checkpoint -force $outputDir/post_place.dcp
report_utilization -file $outputDir/post_place_util.rpt
report_timing_summary -file $outputDir/post_place_timing_summary.rpt -max_paths 1000

puts "Running Routing"
route_design
write_checkpoint -force $outputDir/post_route.dcp
report_utilization -hierarchical -file $outputDir/post_route_util.rpt
report_route_status -file $outputDir/post_route_status.rpt
report_timing_summary -file $outputDir/post_route_timing_summary.rpt -max_paths 1000
report_power -file $outputDir/post_route_power.rpt
report_drc -file $outputDir/post_imp_drc.rpt
reportCriticalPaths $outputDir/post_route_critpath_report.csv

puts "Implementation Done!"
