if {$argc != 1} {
    puts "The script requires one arguments to be inputed."
    puts "\tUsage: xmd -tcl tcl/reset_zynq.tcl [ps7init]"
    exit 1
} else {
    set ps7init [lindex $argv 0]
}
source $ps7init
connect arm hw
rst -system
ps7_init
ps7_post_config
con
