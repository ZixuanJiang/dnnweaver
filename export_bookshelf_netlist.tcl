set leaf_cell_types {
    BUFGCE
    CARRY8
    DSP48E2
    FDCE
    FDPE
    FDRE
    FDSE
    IBUF
    LDCE
    LUT1
    LUT2
    LUT3
    LUT4
    LUT5
    LUT6
    LUT6_2
    MUXF7
    MUXF8
    OBUF
    OBUFT
    RAM32M16
    RAM32X1D
    RAM32X1S
    RAM64X1D
    RAMB18E2
    RAMB36E2
    SRL16E
    SRLC32E
}

proc export_bookshelf_netlist {outdir} {
    # Create a output directory if it doesn't exist
    if {! [file isdirectory $outdir]} {
        file mkdir $outdir
    }
}

# Write bookshelf node file
proc write_bookshelf_node_file {file_name} {
    global leaf_cell_types
    # Get all leaf cells
    set filter_condition [join [prefix_list_elements $leaf_cell_types "REF_NAME == "] " || "]
    set leaf_cells [get_cells -hier -filter $filter_condition]
    # Write all leaf cells to file
    set fh [open $file_name "w"]
    foreach cell $leaf_cells {
        puts $fh "$cell [get_property REF_NAME $cell]"
    }
    close $fh
}

# Write bookshelf hierarchy file
proc write_bookshelf_hierarchy_file {file_name} {
    global leaf_cell_types
    # Get all leaf cells
    set filter_condition [join [prefix_list_elements $leaf_cell_types "REF_NAME == "] " || "]
    set leaf_cells [get_cells -hier -filter $filter_condition]
    # Construct hierarchy
    array set hier {}
    # Write all leaf cells' parent to file
    set fh [open $file_name "w"]
    foreach cell $leaf_cells {
        puts $fh "$cell [get_property REF_NAME $cell]"
    }
    close $fh
}

# Write bookshelf net file
proc write_bookshelf_net_file {file_name} {
    global leaf_cell_types
    # Get all leaf cells
    set filter_condition [join [prefix_list_elements $leaf_cell_types "REF_NAME == "] " || "]
    set leaf_cells [get_cells -hier -filter $filter_condition]
    # For each leaf cell, get its pins and put each of them into the corresponding net entry
    array set net_db {}
    foreach cell $leaf_cells {
        set pins [get_pins -of $cell]
        foreach pin $pins {
            set net [get_nets -of $pin -quiet]
            if {$net eq ""} {
                # This is a floating pin
                continue
            }
            # Get the root net of this net
            # This step is required to merge multiple hierarchical nets into one
            set parent_net [get_property PARENT [get_nets $net]]
            while {$parent_net ne $net} {
                set net $parent_net
                set parent_net [get_property PARENT [get_nets $net]]
            }
            lappend net_db($parent_net) "$cell [get_property REF_PIN_NAME $pin]"
        }
    }
    # Write all net info to file
    # Ignore 1-pin nets and nets tied to VDD/VSS/const
    set fh [open $file_name "w"]
    foreach net [array names net_db] {
        set deg [llength $net_db($net)]
        if {$deg < 2 || [is_power_net $net]} {
            continue
        }
        puts $fh "net $net $deg"
        foreach pin_info $net_db($net) {
            puts $fh "    $pin_info"
        }
        puts $fh "endnet"
    }
    close $fh
}

# Add a prefix to each element in a list
proc prefix_list_elements {ls prefix} {
    set res ""
    foreach e $ls {
        lappend res "${prefix}${e}"
    }
    return $res
}

# Check if a net is a const net (e.g., VDD and VSS)
proc is_power_net {net_name} {
    set net_type [get_property TYPE [get_nets $net_name]]
    if {$net_type eq {POWER} || $net_type eq {GROUND}} {
        return 1
    }
    return 0
}
