# Read arguments
if {$argc != 3 && $argc != 4} {
    puts "The script requires one arguments to be inputed."
    puts "\tUsage: xmd -tcl tcl/run_benchmark.tcl [bitfile] [ps7init] [elffile]"
    exit 1
} else {
    set bitfile [lindex $argv 0]
    set ps7init [lindex $argv 1]
    set elffile [lindex $argv 2]
}

source $ps7init
# Connect to the PS section
connect arm hw
# Reset the system
rst -system
# Program the FPGA
fpga -f $bitfile
# Initialize the PS section (Clock PLL, MIO, DDR etc.)
ps7_init
ps7_post_config
# Load the elf program
dow $elffile
# Start execution
con
