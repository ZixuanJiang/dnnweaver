from math import ceil, floor

serdes_count_bitwidth = 6
pool_iw_bitwidth = 10
pool_oh_bitwidth = 10
pool_kernel_bitwidth = 2
pool_enable_bitwidth = 1
stride_size_bitwidth = 3
layer_type_bitwidth = 2
max_threads_bitwidth = 16
pad_bitwidth = 3
skip_bitwidth = 1
endrow_iw_bitwidth = 10
conv_in_bitwidth = 10
conv_ic_bitwidth = 32
conv_ih_bitwidth = 10
conv_iw_bitwidth = 10
conv_oc_bitwidth = 32
conv_kh_bitwidth = 10
conv_kw_bitwidth = 10

total_bitwidth = \
    pool_iw_bitwidth + \
    pool_oh_bitwidth + \
    pool_kernel_bitwidth + \
    pool_enable_bitwidth + \
    layer_type_bitwidth + \
    max_threads_bitwidth + \
    pad_bitwidth + \
    skip_bitwidth + \
    endrow_iw_bitwidth + \
    conv_in_bitwidth + \
    conv_ic_bitwidth + \
    conv_ih_bitwidth + \
    conv_iw_bitwidth + \
    conv_oc_bitwidth + \
    conv_kh_bitwidth + \
    conv_kw_bitwidth;

AXI_data_bitwidth = 64

mem_addr_width = 32
mem_loop_width = 32
mem_size_width = 20



def ceil_a_by_b(a, b):
    return int(ceil(float(a) / b))


def floor_a_by_b(a, b):
    return int(floor(float(a) / b))


def int_to_bin(num, width):
    #print(num, width)
    if num > pow(2, width):
        print("Number {0} too large for the given bitwidth {1}".format(num, width))
        exit(-1)
    b = bin(num)[2:].zfill(width)
    if num < 0:
        print("Number {0} is negative. Bitwidth = {1}".format(num, width))
        exit(-1)
    #print("Binary = {0}".format(b))
    return b


class DWMacroLayer(object):
    name = ""
    input_dim = []
    output_dim = []
    prev = None
    next = None
    base_data_read_address = None
    base_data_write_address = None
    base_weight_read_address = None
    base_weight_write_address = None
    weight_mem_count = None

    def __init__(self, layer, hardware):

        self.hardware = hardware
        self.slice_size = None
        self.number_of_slices = None

        self.name = layer.name
        self.prev = layer.prev

        self.num_pe = layer.num_pe
        self.num_pu = layer.num_pu
        self.op_width = layer.op_width
        self.axi_num_data = AXI_data_bitwidth / self.op_width

        self.PE_layer = layer
        self.Pool_layer = None
        self.Act_Layer = None

        self.data_mem_offset = None
        self.data_mem_size = None
        self.data_mem_count = None
        self.weight_mem_size = None
        self.weight_mem_offset = None
        self.write_mem_offset = None
        self.write_mem_size = None
        self.write_mem_count = None
        print("Macro Layer Name:\t\t{0}".format(self.name))

    def __str__(self):
        return "PE   : {0:<16}".format(self.PE_layer) + " | \t" + \
               "Pool : {0:<16}".format(self.Pool_layer) + " | \t" + \
               "Act  : {0:<16}".format(self.Act_Layer)

    def set_output_dimensions(self):
        if self.Pool_layer is not None:
            self.output_dim = self.Pool_layer.output_dim
        else:
            self.output_dim = self.PE_layer.output_dim

    def set_input_dimensions(self):
        self.input_dim = self.PE_layer.input_dim

    def append(self, layer):
        self.name += "+" + layer.name
        if isinstance(layer, PoolLayer):
            self.Pool_layer = layer
        else:
            self.Act_Layer = layer

    def get_weight_mem_size(self):
        return self.PE_layer.get_weight_mem_size()

    def get_input_read_size(self):
        return self.PE_layer.get_input_read_size()

    def get_input_read_count(self):
        return self.PE_layer.get_input_read_count()

    def get_weight_read_size(self):
        return self.PE_layer.get_weight_read_size()

    def get_weight_read_count(self):
        return self.PE_layer.get_weight_read_count()

    def get_layer_type(self):
        if isinstance(self.PE_layer, ConvLayer):
            return 0
        elif isinstance(self.PE_layer, FCLayer):
            return 1
        else:
            return 2

    def slice_memory_reads(self):
        self.slice_stream_read_size = []
        self.slice_stream_read_addr = []
        self.slice_packed_stream_size = []
        for i in range(self.number_of_slices):
            if isinstance(self.PE_layer, ConvLayer):

                # This is the number of rows stored in PE buffer
                curr_slice_rows = min(max(self.slice_size, 1), self.input_dim[3] - i * self.slice_size)
                #print("Generating {0} rows for PE output".format(curr_slice_rows))

                # This is the number of rows read by the memory controller for each channel of the input feature map
                slice_read_rows = curr_slice_rows + self.PE_layer.kernel_height - 1
                if i == 0:
                    slice_read_rows -= self.PE_layer.pad
                if i == self.number_of_slices - 1:
                    slice_read_rows -= self.PE_layer.pad
                #print("Current slice read rows = {0}".format(slice_read_rows))

                row_num_axi = ceil_a_by_b(self.input_dim[2], self.num_pe) * \
                              ceil_a_by_b(self.num_pe, self.axi_num_data)
                row_size = row_num_axi * self.axi_num_data * self.op_width / 8

                curr_slice_read_size = row_num_axi * slice_read_rows
                self.slice_stream_read_size.append(curr_slice_read_size)

                slice_read_offset = ceil_a_by_b(self.input_dim[2], self.num_pe) * \
                                    self.slice_size * \
                                    ceil_a_by_b(self.num_pe, self.axi_num_data) * 8

                # For the read_info module
                packed_stream_read_size = curr_slice_read_size * self.axi_num_data / self.num_pe
                self.slice_packed_stream_size.append(packed_stream_read_size)

                if i > 0:
                    negative_offset = int(self.PE_layer.kernel_height / 2)
                else:
                    negative_offset = 0
                curr_slice_read_addr = self.base_data_read_address + i * slice_read_offset - (negative_offset * row_size)
                self.slice_stream_read_addr.append(curr_slice_read_addr)

                #print("Slice addr = {0}".format(hex(curr_slice_read_addr)))
                #print("Base addr = {0}".format(hex(self.base_data_read_address)))
                #print("negative offset = {0}".format(negative_offset))
                #print("Row size = {0}".format(row_size))

            elif isinstance(self.PE_layer, LRNLayer):
                curr_slice_read_size = self.stream_read_size
                self.slice_stream_read_size.append(curr_slice_read_size)
                #print("LRN slice read size = {0}".format(curr_slice_read_size))

                packed_stream_read_size = curr_slice_read_size * self.axi_num_data / self.num_pe
                self.slice_packed_stream_size.append(packed_stream_read_size)

                curr_slice_read_addr = self.base_data_read_address
                self.slice_stream_read_addr.append(curr_slice_read_addr)

            else:
                packed_stream_read_size = self.stream_read_size * self.axi_num_data / self.num_pe
                self.slice_packed_stream_size.append(packed_stream_read_size)
                curr_slice_read_addr = self.base_weight_read_address
                self.slice_stream_read_addr.append(curr_slice_read_addr)
                curr_slice_read_size = self.stream_read_size
                self.slice_stream_read_size.append(curr_slice_read_size)

    def generate_compute_instructions(self):

        print("\n\n")
        print("*"*50)
        print("generating instructions for macro layer {0}".format(self.name))
        print("Layer name = {0}".format(self.name))

        self.set_input_dimensions()
        self.set_output_dimensions()

        print("Layer input  Dim = {0}".format(self.input_dim))
        print("Layer output Dim = {0}".format(self.output_dim))

        self.input_dim = self.PE_layer.input_dim
        if self.Pool_layer is not None:
            self.output_dim = self.PE_layer.output_dim
        else:
            self.output_dim = self.PE_layer.output_dim

        _pad = self.PE_layer.pad
        _kh = self.PE_layer.kernel_height
        _kw = self.PE_layer.kernel_width
        _stride = self.PE_layer.stride

        if isinstance(self.PE_layer, ConvLayer):
            _in = self.PE_layer.input_dim[0]
            _ic = self.PE_layer.input_dim[1]
            _iw = self.PE_layer.input_dim[2]
            _ih = self.PE_layer.input_dim[3]
            _on = _in
            _oc = self.PE_layer.output_dim[1]
            _ow = (_iw + 2 * _pad - _kh) / self.PE_layer.stride + 1
            _oh = (_ih + 2 * _pad - _kh) / self.PE_layer.stride + 1
            _max_threads = _ow
            _endrow_iw = int(floor((_ih - _kh + 1 + _pad) / float(self.num_pe)))
        elif isinstance(self.PE_layer, FCLayer):
            _in = self.input_dim[0]
            _ic = self.input_dim[1] * self.input_dim[2] * self.input_dim[3]
            _iw = 1
            _ih = 1
            _on = _in
            _oc = int(ceil(self.PE_layer.output_dim[1] / float(self.num_pe)))
            _ow = 1
            _oh = 1
            _max_threads = self.output_dim[1]
            _endrow_iw = 8
            _stride = 1
        else:
            #_oc = ceil_a_by_b(self.output_dim[1], self.num_pu)
            _kw = self.PE_layer.local_size
            _kh = self.PE_layer.local_size
            _in = self.input_dim[0]
            _ic = 1
            _iw = self.input_dim[2]
            _ih = self.input_dim[3]
            _on = _in 
            _oc = self.output_dim[1]
            _ow = self.output_dim[2]
            _oh = self.output_dim[3]
            _max_threads = _ow
            _endrow_iw = int(floor((_ih - _kh + 1 + _pad) / float(self.num_pe)))
            _stride = 1
        print("in:  {0} x {1} x {2} x {3}".format(_in, _ic, _iw, _ih))
        print("out: {0} x {1} x {2} x {3}".format(_on, _oc, _ow, _oh));

        iw_padded = int(ceil(float(_iw) / self.num_pe)) * self.num_pe
        ow_padded = int(ceil(float(_ow) / self.num_pe)) * self.num_pe

        if iw_padded != ow_padded * _stride:
            _skip = 1
        else:
            _skip = 0

        _iw = int(ceil(float(_ow) / float(self.num_pe))) - 1
        if (isinstance(self.PE_layer, ConvLayer)):
            _oc = int(ceil(_oc / float(self.num_pu)))

        if ow_padded % (2 * self.num_pe) != 0:
            _pool_iw = _iw + 1
        else:
            _pool_iw = _iw

            # if self.next is not None and isinstance(self.next.PE_layer, FCLayer):
            # _pool_iw = _iw

        # _pool_iw = int(ceil(float(_iw)/2)*2)

        if self.Pool_layer is not None:
            # TODO: Change back to self.Pool_layer.kernel_width
            _pool_kernel = 2
            _pool_enable = 1
        else:
            _pool_kernel = 0
            _pool_enable = 0

        # print("Pool Enabled     = {0}".format(_pool_enable))
        # print("Pool Kernel size = {0}".format(_pool_kernel))
        # print("Output channels  = {0}".format(_oc))
        # print("Stride           = {0}".format(_stride))

        od = self.output_dim
        if self.Pool_layer is not None:
            od = self.Pool_layer.output_dim

        if self.next is not None and isinstance(self.next.PE_layer, FCLayer):
            next_node_is_FC = True
        else:
            next_node_is_FC = False

        if od[2] % self.num_pe != 0 and next_node_is_FC and isinstance(self.PE_layer, ConvLayer):
            serdes_count = od[2] % self.num_pe
            # print("SerDes Count = {0}".format(serdes_count))
            # exit(-1)
        else:
            serdes_count = self.num_pe
        # print("SerDes Count = {0}".format(serdes_count))

        # print(self.hardware["resources"]["memory_per_bram"])

        # TODO: find lower bound on this
        scratch_space = 128
        scratch_space_needed = ceil_a_by_b(self.input_dim[2], self.num_pe) * self.PE_layer.kernel_height - 1
        # print("Assigned scratch space = {0}; required = {1}".format(scratch_space, scratch_space_needed))

        # if scratch_space_needed > scratch_space:
            # print("Error: Scratch space needed exceeds assigned space")

        bram_size = self.hardware["resources"]["memory_per_bram"]
        # TODO: factor of 2 added
        bram_depth = ceil_a_by_b(bram_size, self.op_width) / 2
        # print("BRAM depth = {0}".format(bram_depth))

        result_depth = bram_depth - scratch_space
        # print("BRAM for result slice = {0}".format(result_depth))

        bram_per_row = ceil_a_by_b(self.output_dim[2], self.num_pe)
        rows_per_slice = min(floor_a_by_b(result_depth, bram_per_row), self.PE_layer.output_dim[3])
        # print("Max rows per slice = {0}".format(rows_per_slice))

        number_of_slices = ceil_a_by_b(self.output_dim[2], rows_per_slice)
        # print("Number of slices = {0}".format(number_of_slices))

        self.slice_size = max(min(rows_per_slice, _oh), 1)
        self.number_of_slices = number_of_slices

        tb = []

        if isinstance(self.PE_layer, FCLayer):
            _ic = _ic + 1

        for ii in range(number_of_slices):
            slice_size = min(rows_per_slice, _oh)
            if ii == 0:
                _pad_r_s = _pad
            else:
                _pad_r_s = 0

            if ii == (number_of_slices - 1):
                _pad_r_e = _pad
                if rows_per_slice * number_of_slices > self.output_dim[2]:
                    slice_size = self.output_dim[2] % rows_per_slice
            else:
                _pad_r_e = 0

            # print("slice {0} - Pad_W: {1} Pad_R_S: {2} Pad_R_E: {3}".format(ii, _pad, _pad_r_s, _pad_r_e))
            # print("slice size = {0}".format(slice_size))

            _oh = slice_size
            _ih = (_oh - 1) * self.PE_layer.stride - _pad_r_e - _pad_r_s + _kh

            # print("OH = {0}".format(_oh))
            # print("IH = {0}".format(_ih))
            # print("Pad = {0}".format(self.PE_layer.pad))
            # print("Pad_r_s = {0}".format(_pad_r_s))
            # print("Pad_r_e = {0}".format(_pad_r_e))
            # print("KH = {0}".format(_kh))
            # print("stride = {0}".format(self.PE_layer.stride))

            text_buffer = \
                int_to_bin(serdes_count, serdes_count_bitwidth) + \
                int_to_bin(_stride, stride_size_bitwidth) + \
                int_to_bin(_pool_iw, pool_iw_bitwidth) + \
                int_to_bin(_oh - 1, pool_oh_bitwidth) + \
                int_to_bin(_pool_kernel, pool_kernel_bitwidth) + \
                int_to_bin(_pool_enable, pool_enable_bitwidth) + \
                int_to_bin(self.get_layer_type(), layer_type_bitwidth) + \
                int_to_bin(_max_threads, max_threads_bitwidth) + \
                int_to_bin(_pad, pad_bitwidth) + \
                int_to_bin(_pad_r_s, pad_bitwidth) + \
                int_to_bin(_pad_r_e, pad_bitwidth) + \
                int_to_bin(_skip, skip_bitwidth) + \
                int_to_bin(_endrow_iw, endrow_iw_bitwidth) + \
                int_to_bin(_ic - 1, conv_ic_bitwidth) + \
                int_to_bin(_ih - 1, conv_ih_bitwidth) + \
                int_to_bin(_iw, conv_iw_bitwidth) + \
                int_to_bin(_oc - 1, conv_oc_bitwidth) + \
                int_to_bin(_kh - 1, conv_kh_bitwidth) + \
                int_to_bin(_kw - 1, conv_kw_bitwidth) + "\n"

            tb.append(text_buffer)

        return tb

    def generate_memory_read_binary(self):

        print("generating memory instructions")
        print("Layer name = {0}".format(self.name))
        print("Layer input  Dim = {0}".format(self.PE_layer.input_dim))
        print("Layer output Dim = {0}".format(self.PE_layer.output_dim))

        self.set_output_dimensions()

        self.data_mem_size = self.get_input_read_size() / self.axi_num_data
        self.data_mem_offset = self.data_mem_size * 8
        self.data_mem_count = self.get_input_read_count()

        if self.base_data_read_address is None:
            self.base_data_read_address = self.prev.base_data_write_address
        self.base_data_write_address = self.base_data_read_address + self.data_mem_size * self.PE_layer.input_dim[1] * 8

        self.weight_mem_size = self.get_weight_read_size() / self.axi_num_data
        self.weight_mem_offset = self.weight_mem_size * 8
        self.weight_mem_count = self.get_weight_read_count()

        #print("Base Data Read Address = {0}".format(hex(self.base_data_read_address)))
        #print("Data Read Size = {0}".format(self.data_mem_size))
        #print("Data Read Offset = {0}".format(self.data_mem_offset))
        #print("Data Read Count = {0}".format(self.data_mem_count))

        if self.base_weight_read_address is None:
            self.base_weight_read_address = self.prev.base_weight_read_address + self.prev.PE_layer.get_weight_mem_size()

        #print("Base Weight Read Address = {0}".format(hex(self.base_weight_read_address)))
        #print("Weight Read Size = {0}".format(self.weight_mem_size))
        #print("Weight Read Offset = {0}".format(self.weight_mem_offset))
        #print("Weight Read Count = {0}".format(self.weight_mem_count))

        #print("Number of slices = {0}".format(self.slice_size))

        self.stream_read_loop1_offset = 0
        self.stream_read_loop2_offset = 0

        if isinstance(self.PE_layer, ConvLayer):
            self.buffer_read_address = self.base_weight_read_address
            self.buffer_read_size = self.weight_mem_size
            self.buffer_read_offset = self.weight_mem_offset
            self.buffer_read_count = self.weight_mem_count

            self.stream_read_address = self.base_data_read_address
            self.stream_read_size = self.data_mem_size
            self.stream_read_loop0_offset = self.data_mem_offset
            self.stream_read_loop0_count = self.PE_layer.input_dim[1]
            self.stream_read_loop1_count = ceil_a_by_b(self.PE_layer.output_dim[1], self.num_pu)
            self.stream_read_loop2_count = 1
        elif isinstance(self.PE_layer, LRNLayer):
            self.buffer_read_count = 1
            self.buffer_read_address = self.base_weight_read_address
            self.buffer_read_size = self.weight_mem_size
            self.buffer_read_offset = self.weight_mem_offset

            self.stream_read_address = self.base_data_read_address
            # Read one row for each PU
            #self.stream_read_size = self.data_mem_size / self.input_dim[3]
            #self.stream_read_loop0_count = self.num_pu
            self.stream_read_size = self.data_mem_size
            self.stream_read_loop0_count = self.input_dim[1]
            self.stream_read_loop0_offset = self.PE_layer.get_input_read_size() / self.axi_num_data * 8
            #self.stream_read_loop1_offset = self.stream_read_size * 8
            self.stream_read_loop1_offset = 0
            #print("LRN loop0 offset = {0}".format(self.stream_read_loop0_offset))

            #self.stream_read_loop1_count = self.input_dim[3]
            #self.stream_read_loop2_count = self.input_dim[1]
            self.stream_read_loop1_count = 1
            self.stream_read_loop2_count = 1
        else:
            self.buffer_read_address = self.base_data_read_address
            self.buffer_read_size = self.data_mem_size
            self.buffer_read_offset = self.data_mem_offset
            self.buffer_read_count = self.data_mem_count

            self.stream_read_address = self.base_weight_read_address
            self.stream_read_size = self.weight_mem_size
            self.stream_read_loop0_offset = self.weight_mem_offset
            self.stream_read_loop0_count = self.weight_mem_count
            self.stream_read_loop1_count = 1
            self.stream_read_loop2_count = 1

        packed_buffer_read_size = self.buffer_read_size
        #print("Packed Buffer Read Size = {0}".format(packed_buffer_read_size))

        tb = []

        # Divide the PE's computations into slices
        self.slice_memory_reads()

        for i in range(self.number_of_slices):
            curr_slice_size = self.slice_stream_read_size[i]
            curr_slice_addr = self.slice_stream_read_addr[i]
            packed_stream_read_size = self.slice_packed_stream_size[i]

            #print("Curr Slice Size = {0}".format(curr_slice_size))
            #print("Stream addr = {0}".format(hex(curr_slice_addr)))
            #print("Buffer addr = {0}".format(hex(self.buffer_read_address)))
            #print("Buffer offset = {0}".format(self.buffer_read_offset))
            # print('stream_read_loop0_count = {}'.format(self.stream_read_loop0_count-1))
            # print('stream_read_loop0_offset = {}'.format(self.stream_read_loop0_offset))
            text_buffer = \
                int_to_bin(self.get_layer_type(), layer_type_bitwidth) + \
                int_to_bin(packed_stream_read_size, mem_size_width) + \
                int_to_bin(curr_slice_addr, mem_addr_width) + \
                int_to_bin(curr_slice_size, mem_size_width) + \
                int_to_bin(self.stream_read_loop0_offset, mem_addr_width) + \
                int_to_bin(self.stream_read_loop1_offset, mem_addr_width) + \
                int_to_bin(self.stream_read_loop2_offset, mem_addr_width) + \
                int_to_bin(self.stream_read_loop0_count - 1, mem_loop_width) + \
                int_to_bin(self.stream_read_loop1_count - 1, mem_loop_width) + \
                int_to_bin(self.stream_read_loop2_count - 1, mem_loop_width) + \
                int_to_bin(packed_buffer_read_size, mem_size_width) + \
                int_to_bin(self.buffer_read_address, mem_addr_width) + \
                int_to_bin(self.buffer_read_size, mem_size_width) + \
                int_to_bin(self.buffer_read_offset, mem_addr_width) + \
                int_to_bin(self.buffer_read_count - 1, mem_addr_width) + \
                "\n"
            tb.append(text_buffer)

        return tb

    def generate_memory_write_binary(self):

        print("generating memory instructions")
        print("Layer name = {0}".format(self.name))
        print("Layer output Dim = {0}".format(self.output_dim))
        if self.Pool_layer is not None:
            self.output_dim = self.Pool_layer.output_dim
        od = self.output_dim
        if self.next is not None and isinstance(self.next.PE_layer, FCLayer):
            next_is_FC = True
            #print("next is FC. output size = {0}".format(od[1] * od[2] * od[3]))
        else:
            next_is_FC = False

        if isinstance(self.PE_layer, ConvLayer) and not (next_is_FC):
            output_fm_size = int(ceil(float(od[2]) / self.num_pe)) * od[3] * int(
                ceil(float(self.num_pe) / self.axi_num_data)) * self.axi_num_data
        else:
            output_fm_size = int(ceil(float(od[1] * od[2] * od[3]) / self.num_pe)) * int(
                ceil(float(self.num_pe) / self.axi_num_data)) * \
                             self.axi_num_data
            #if next_is_FC:
                #print("output_dm_size = {0}".format(output_fm_size))
                #print(od)
                # exit(-1)

        self.write_mem_size = output_fm_size / self.axi_num_data
        self.write_mem_offset = self.write_mem_size * 8

        if isinstance(self.PE_layer, ConvLayer):
            self.write_mem_count = int(ceil(float(od[1]) / self.num_pu)) * self.num_pu
        else:
            self.write_mem_count = self.num_pu

        #print("Output FM size = {0}".format(output_fm_size))

        #print("Base Data Write Address = {0}".format(hex(self.base_data_write_address)))
        #print("Data Write Size = {0}".format(self.write_mem_size))
        #print("Data Write Offset = {0}".format(self.write_mem_offset))
        #print("Data Write Count = {0}".format(self.write_mem_count))

        tb = []
        for i in range(self.number_of_slices):

            if isinstance(self.PE_layer, ConvLayer) and not (next_is_FC):

                if i == 0:
                    pad_r_s = self.PE_layer.pad
                else:
                    pad_r_s = 0

                if i == self.number_of_slices - 1:
                    pad_r_e = self.PE_layer.pad
                    if i == self.number_of_slices - 1 and self.slice_size * self.number_of_slices > self.input_dim[3]:
                        curr_slice_rows = self.input_dim[3] % self.slice_size
                    else:
                        curr_slice_rows = self.slice_size
                else:
                    pad_r_e = 0
                    curr_slice_rows = self.slice_size

                if self.Pool_layer is None:
                    _stride = 1
                else:
                    _stride = self.Pool_layer.stride

                curr_slice_rows = ceil_a_by_b(curr_slice_rows, _stride)

                #print("Current write slice rows = {0}".format(curr_slice_rows))
                #print("Current output = {0}".format(self.output_dim[2]))

                curr_slice_size = ceil_a_by_b(self.output_dim[2], self.num_pe) * \
                                  curr_slice_rows * \
                                  ceil_a_by_b(self.num_pe, self.axi_num_data)

                curr_slice_addr = self.base_data_write_address + i * self.write_mem_offset

            elif isinstance(self.PE_layer, LRNLayer):
                curr_slice_size = ceil_a_by_b(self.output_dim[2], self.num_pe) * \
                                  self.output_dim[3] * \
                                  ceil_a_by_b(self.num_pe, self.axi_num_data)
                                  #ceil_a_by_b(self.output_dim[1], self.num_pu)
                curr_slice_addr = self.base_data_write_address
                self.write_mem_count = self.output_dim[1]

            else:
                curr_slice_size = ceil_a_by_b(od[1] * od[2] * od[3], self.num_pe) * \
                                  ceil_a_by_b(self.num_pe, self.axi_num_data)
                curr_slice_addr = self.base_data_write_address
                if next_is_FC and isinstance(self.PE_layer, ConvLayer):
                    curr_slice_size = ceil_a_by_b(od[2] * od[3], self.num_pe) * \
                                      ceil_a_by_b(self.num_pe, self.axi_num_data)

            #print("Curr Slice Size = {0}".format(curr_slice_size))
            self.write_mem_offset = curr_slice_size * 8
            #print("Curr Slice Offset = {0}".format(self.write_mem_offset))

            text_buffer = \
                int_to_bin(self.get_layer_type(), layer_type_bitwidth) + \
                int_to_bin(curr_slice_addr, mem_addr_width) + \
                int_to_bin(curr_slice_size, mem_size_width) + \
                int_to_bin(self.write_mem_offset, mem_addr_width) + \
                int_to_bin(self.write_mem_count - 1, mem_loop_width) + \
                "\n"

            tb.append(text_buffer)

        return tb


class DWlayer(object):
    name = None
    type = None
    input_dim = []
    output_dim = []
    prev = None
    next = None
    base_data_read_address = None
    base_data_write_address = None
    base_weight_read_address = None
    base_weight_write_address = None
    weight_mem_count = None

    def __init__(self, layer, num_pe, num_pu, op_width):
        self.name = layer.name
        self.type = layer.type
        self.prev = layer.bottom
        self.num_pe = num_pe
        self.num_pu = num_pu
        self.op_width = op_width
        self.axi_num_data = AXI_data_bitwidth / op_width
        self.data_mem_offset = None
        self.data_mem_size = None
        self.data_mem_count = None
        self.weight_mem_size = None
        self.weight_mem_offset = None
        self.write_mem_offset = None
        self.write_mem_size = None
        self.write_mem_count = None
        self.stride = 1
        self.pad = 0
        self.kernel_width = 1
        self.kernel_height = 1
        print("Layer Name:\t\t{0}".format(self.name))

    def get_output_dim(self):
        self.output_dim = []

    def get_weight_size(self):
        return 0

    def set_input_dim(self, input_dim):
        self.input_dim = input_dim


class ConvLayer(DWlayer):
    def __init__(self, layer, num_pe, num_pu, op_width):
        super(self.__class__, self).__init__(layer, num_pe, num_pu, op_width)
        if layer.convolution_param.kernel_w is not 0:
            self.kernel_width = layer.convolution_param.kernel_w
        else:
            self.kernel_width = layer.convolution_param.kernel_size
        if layer.convolution_param.kernel_h is not 0:
            self.kernel_height = layer.convolution_param.kernel_h
        else:
            self.kernel_height = layer.convolution_param.kernel_size
        self.output_channels = layer.convolution_param.num_output
        self.num_groups = layer.convolution_param.group
        self.stride = layer.convolution_param.stride
        self.pad = layer.convolution_param.pad
        print("Layer Type:\t\tConvolution {0}x{1} - s{2}".format(self.kernel_width,
                                                                 self.kernel_height,
                                                                 self.stride))

    def __str__(self):
        return "{0} {1}x{2} s{3}".format(self.name, self.kernel_height, self.kernel_height, self.stride)

    def get_output_dim(self):
        if len(self.output_dim) == 0:
            if len(self.input_dim) == 0:
                self.input_dim = self.prev.output_dim

            self.output_dim.append(self.input_dim[0])
            self.output_dim.append(self.output_channels)
            self.output_dim.append((self.input_dim[2] - self.kernel_width + 2 * self.pad) / self.stride + 1)
            self.output_dim.append((self.input_dim[3] - self.kernel_height + 2 * self.pad) / self.stride + 1)

        return self.output_dim

    def get_input_read_size(self):
        # input_read_size = self.input_dim[0] * \
        input_read_size = 1 *\
                          ceil_a_by_b(self.input_dim[2], self.num_pe) * \
                          self.input_dim[3] * \
                          ceil_a_by_b(self.num_pe, self.axi_num_data) * \
                          self.axi_num_data
        return input_read_size

    def get_input_read_count(self):
        return self.input_dim[1] * int(ceil(float(self.output_channels) / self.num_pu))

    def get_weight_dim(self):
        return [self.output_channels, self.input_dim[1], self.kernel_height, self.kernel_width]

    def get_weight_mem_size(self):
        weight_size = int(ceil(float(self.kernel_height * self.kernel_width) / self.axi_num_data) + 1) * \
                      self.axi_num_data * \
                      self.input_dim[1] * self.output_dim[1]
        return weight_size * self.op_width / 8

    def get_weight_read_size(self):
        return (ceil_a_by_b(self.kernel_width * self.kernel_height, self.axi_num_data) + 1) * self.axi_num_data

    def get_weight_read_count(self):
        return self.num_pu


class PoolLayer(DWlayer):
    def __init__(self, layer, num_pe, num_pu, op_width):
        super(self.__class__, self).__init__(layer, num_pe, num_pu, op_width)
        self.kernel_width = layer.pooling_param.kernel_size
        self.kernel_height = layer.pooling_param.kernel_size
        self.stride = layer.pooling_param.stride
        print("Layer Type:\t\tPooling {0}x{1} - s{2}".format(self.kernel_width,
                                                             self.kernel_height,
                                                             self.stride))

    def __str__(self):
        return "{0} {1}x{2} s{3}".format(self.name, self.kernel_height, self.kernel_height, self.stride)

    def get_output_dim(self):
        if len(self.input_dim) == 0:
            self.output_dim = []
        else:
            self.output_dim.append(self.input_dim[0])
            self.output_dim.append(self.input_dim[1])
            self.output_dim.append(int(ceil(float(self.input_dim[2] - self.kernel_width) / self.stride)) + 1)
            self.output_dim.append(int(ceil(float(self.input_dim[3] - self.kernel_height) / self.stride)) + 1)

    def get_weight_size(self):
        return 0


class FCLayer(DWlayer):
    def __init__(self, layer, num_pe, num_pu, op_width):
        super(self.__class__, self).__init__(layer, num_pe, num_pu, op_width)
        self.output_channels = layer.inner_product_param.num_output
        print("Layer Type:\t\tFullyConnected ".format(self.output_channels))

    def __str__(self):
        return "{0} {1}x{2}".format(self.name, self.input_dim[1], self.output_channels)

    def get_output_dim(self):
        if len(self.input_dim) == 0:
            self.output_dim = []
        else:
            self.output_dim.append(self.input_dim[0])
            self.output_dim.append(self.output_channels)
            self.output_dim.append(1)
            self.output_dim.append(1)

    def get_weight_size(self):
        input_fm_size = self.input_dim[1] * self.input_dim[2] * self.input_dim[3]
        weight_size = int(ceil(input_fm_size / float(self.num_pe))) * self.output_channels + 1
        return weight_size * 8

    def get_weight_dim(self):
        input_fm_size = self.input_dim[1] * self.input_dim[2] * self.input_dim[3]
        return [self.output_channels, 1, input_fm_size, 1]

    def get_weight_mem_size(self):
        id = self.input_dim
        input_fm_size = id[1] * id[2] * id[3] + 1
        weight_size = int(ceil(float(self.output_dim[1]) / self.num_pe)) * \
                      int(ceil(float(self.num_pe) / self.axi_num_data)) * self.axi_num_data * \
                      input_fm_size
        return weight_size * self.op_width / 8

    def get_input_read_size(self):
        # input_read_size = ceil_a_by_b(self.input_dim[0] * self.input_dim[1] * self.input_dim[2] * self.input_dim[3], self.num_pe) * \
                          # ceil_a_by_b(self.num_pe, self.axi_num_data) * self.axi_num_data
        input_read_size = ceil_a_by_b(1 * self.input_dim[1] * self.input_dim[2] * self.input_dim[3], self.num_pe) * \
                          ceil_a_by_b(self.num_pe, self.axi_num_data) * self.axi_num_data
        return input_read_size

    def get_input_read_count(self):
        return self.num_pu

    def get_weight_read_size(self):
        return ceil_a_by_b(self.output_channels, self.num_pe) * \
               ceil_a_by_b(self.num_pe, self.axi_num_data) * \
               (self.input_dim[1] * self.input_dim[2] * self.input_dim[3] + 1) * self.axi_num_data

    def get_weight_read_count(self):
        return 1

class ReluLayer(DWlayer):
    def __init__(self, layer, num_pe, num_pu, op_width):
        super(self.__class__, self).__init__(layer, num_pe, num_pu, op_width)
        print("Layer Type:\t\tReLU")

    def __str__(self):
        return "{0} {1}".format(self.name, "ReLU")

    def get_output_dim(self):
        if len(self.input_dim) == 0:
            self.output_dim = []
        else:
            self.output_dim.append(self.input_dim[0])
            self.output_dim.append(self.input_dim[1])
            self.output_dim.append(self.input_dim[2])
            self.output_dim.append(self.input_dim[3])

    def get_weight_size(self):
        return 0

class LRNLayer(DWlayer):
    def __init__(self, layer, num_pe, num_pu, op_width):
        super(self.__class__, self).__init__(layer, num_pe, num_pu, op_width)
        print(layer)
        self.local_size = layer.lrn_param.local_size
        self.output_channels = None
        self.pad = floor_a_by_b(self.local_size, 2)
        print("Layer Type:\t\tNormalization {0}x{1}".format(self.local_size, self.local_size))

    def __str__(self):
        return "{0} {1}x{2}".format(self.name, self.local_size, self.local_size)

    def get_output_dim(self):
        if len(self.output_dim) == 0:
            if len(self.input_dim) == 0:
                self.input_dim = self.prev.output_dim

            self.output_channels = self.input_dim[1]
            self.output_dim.append(self.num_pu)
            self.output_dim.append(self.input_dim[1])
            self.output_dim.append(self.input_dim[2] - self.local_size + 2 * self.pad + 1)
            self.output_dim.append(self.input_dim[3] - self.local_size + 2 * self.pad + 1)

        return self.output_dim

    def get_input_read_size(self):
        input_read_size = ceil_a_by_b(self.input_dim[2], self.num_pe) * \
                          self.input_dim[3] * \
                          ceil_a_by_b(self.num_pe, self.axi_num_data) * \
                          self.axi_num_data
        return input_read_size

    def get_input_read_count(self):
        return self.input_dim[1] * int(ceil(float(self.output_channels) / self.num_pu))

    def get_weight_dim(self):
        return [0,0,0,0]

    def get_weight_mem_size(self):
        return 0

    def get_weight_read_size(self):
        return 0

    def get_weight_read_count(self):
        return 0
