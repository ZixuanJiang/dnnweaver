# from network import LayerNode, Convolution
import sys
from math import ceil, log, floor

from collections import deque

INPUT_SHARING = False


class DFG:
    def __init__(self, conv, hardware):
        self.hardware = hardware
        total_bram_capacity = self.hardware["resources"]["num_bram"] * self.hardware["resources"]["memory_per_bram"]
        self.memory = total_bram_capacity
        self.compute_config = hardware["config"]

    def schedule(self, layer):
        # print
        from network import Convolution, Normalization
        from network import Pooling
        if isinstance(layer, Convolution):
            tmp = self.conv_schedule(layer)
            # print tmp
            return tmp

        if isinstance(layer, Normalization):
            print "Scheduling Normalization"
            # exit(-1)
            tmp = self.norm_schedule(layer)
            # print tmp
            return tmp
        # elif isinstance(layer, Pooling):
        #     return [[1, 1, 1], 0]
        else:
            print "Unknown Layer"
            return [[1, 1, 1, 1, 1, 1], 0]
            # sys.exit(-1)

    def conv_schedule(self, conv):
        from network import Convolution
        assert isinstance(conv, Convolution)

        prev_layer_params = conv.prev_layer.params
        self.input_width = prev_layer_params["size_x"]
        self.input_height = prev_layer_params["size_y"]
        self.input_channels = prev_layer_params["output_channels"]
        self.output_channels = conv.params["output_channels"]
        self.kernel_width = conv.params["kernel_size"]
        self.kernel_height = conv.params["kernel_size"]
        od = conv.get_output_dimensions()
        print "OUTPUT DIMENSIONS ARE ------------ {0}".format(od)
        self.output_width = od[0]
        self.output_height = od[1]
        self.pad_x = conv.params["pad_x"]
        self.pad_y = conv.params["pad_y"]
        self.stride_x = conv.params["stride_x"]
        self.stride_y = conv.params["stride_y"]

        [input_block, output_block] = self.smart_force(conv)

        print "Obtained the following config - Input : {0}, output - {1}".format(input_block, output_block)
        # print "Input partition  = {0}".format(input_partition)
        # print "Output partition = {0}".format(output_partition)
        conv.set_data_partition(input_block, output_block)
        # config = self.brute_force()
        # penalty = self.get_penalty_print(config)
        penalty = self.get_penalty_print(input_block, output_block, conv)
        # penalty = 0
        # print "Scheduling CONV"
        # print "Min Penalty          = {0:,}".format(penalty)
        # print [config, penalty]
        conv.set_memory_accesses(penalty)
        # exit(-1)
        return [input_block, output_block, penalty]


    def norm_schedule(self, norm):
        from network import Normalization
        assert isinstance(norm, Normalization)

        prev_layer_params = norm.prev_layer.params
        self.input_width = prev_layer_params["size_x"]
        self.input_height = prev_layer_params["size_y"]
        self.input_channels = prev_layer_params["output_channels"]
        self.output_channels = norm.params["output_channels"]
        self.norm_type = norm.norm_type
        self.kernel_width = norm.params["kernel_size"]
        if (self.norm_type == "within_channel"):
            self.kernel_height = norm.params["kernel_size"]
        else:
            self.kernel_height = 1

        od = norm.get_output_dimensions()
        print "OUTPUT DIMENSIONS ARE ------------ {0}".format(od)
        self.output_width = od[0]
        self.output_height = od[1]
        self.pad_x = norm.params["pad_x"]
        self.pad_y = norm.params["pad_y"]
        self.stride_x = norm.params["stride_x"]
        self.stride_y = norm.params["stride_y"]

        [input_block, output_block] = self.smart_force_norm(norm)
        # exit(-1)

        print "Obtained the following config - Input : {0}, output - {1}".format(input_block, output_block)
        # print "Input partition  = {0}".format(input_partition)
        # print "Output partition = {0}".format(output_partition)
        # norm.set_data_partition(input_block, output_block)
        # config = self.brute_force()
        # penalty = self.get_penalty_print(config)
        penalty = self.get_penalty_print_norm(input_block, output_block, norm)
        # penalty = 0
        # print "Scheduling norm"
        # print "Min Penalty          = {0:,}".format(penalty)
        # print [config, penalty]
        norm.set_memory_accesses(penalty)
        # exit(-1)
        return [input_block, output_block, penalty]

    def pool_schedule(self, pool):
        from network import Pooling
        assert isinstance(pool, Pooling)
        prev_layer_params = pool.prev_layer.params
        # self.input_width = prev_layer_params["size_x"]
        # self.input_height = prev_layer_params["size_y"]
        # self.input_channels = prev_layer_params["output_channels"]
        # self.output_channels = pool.params["output_channels"]
        # self.kernel_width = pool.params["kernel_size"]
        # self.kernel_height = pool.params["kernel_size"]
        # od = pool.get_output_dimensions()
        # self.output_width = od[0]
        # self.output_height = od[1]
        #
        # config = self.smart_force()
        # config = self.brute_force()
        # penalty = self.get_penalty_print(config)
        print "Min Penalty          = {0:,}".format(0)

    def get_max_width(self, id, od, oh_min):
        on_chip_memory = self.memory / 8
        print "Total on-chip memory = {0}".format(on_chip_memory)
        print "Compute Config = {0}".format(self.compute_config)
        # memory_per_pu = int(floor(float(on_chip_memory) / self.compute_config[2]))
        memory_per_pu = self.compute_config[0] * self.hardware["resources"]["memory_per_bram"] / 8
        print "Memory per BRAM = {0:,}".format(self.hardware["resources"]["memory_per_bram"])
        print "Memory per PU = {0:,} Bytes".format(memory_per_pu)
        kw = self.kernel_width
        kh = self.kernel_height

        # ih = kh
        ih = 1

        for ow in range(self.compute_config[0], self.output_width + 1, self.compute_config[0]):
            memory_for_output = int(ceil(float(ow) / self.compute_config[0]) * self.compute_config[0]) * oh_min * od * \
                                self.hardware["data"]["bytes_per_element"]
            # iw = (ow - 1) * self.stride_x + kw
            # iw = 2 * self.compute_config[0]
            iw = 0
            memory_for_input = int(ceil(float(iw) / self.compute_config[0]) * self.compute_config[0]) * kh * id
            # print "Memory for input = {0}".format(memory_for_input)
            # memory_for_input = 0
            if memory_for_input + memory_for_output > memory_per_pu:
                return ow - self.compute_config[0]

        return self.output_width

    def get_max_height(self, id, od, ow_max):
        on_chip_memory = self.memory / 8
        print "Total on-chip memory = {0}".format(on_chip_memory)
        print "Compute Config = {0}".format(self.compute_config)
        # memory_per_pu = int(floor(float(on_chip_memory) / self.compute_config[2]))
        memory_per_pu = self.compute_config[0] * self.hardware["resources"]["memory_per_bram"] / 8
        print "Memory per PU = {0:,} Bytes".format(memory_per_pu)
        kw = self.kernel_width
        kh = self.kernel_height
        iw = (ow_max - 1) * self.stride_x + kw

        for oh in range(1, self.output_height + 1):
            memory_for_output = int(ceil(float(ow_max) / self.compute_config[0]) * self.compute_config[0]) * oh * od * \
                                self.hardware["data"]["bytes_per_element"]
            # ih = (oh - 1) * self.stride_y + kh
            ih = 1
            # memory_for_input = iw * ih * id
            memory_for_input = 0
            if memory_for_input + memory_for_output > memory_per_pu:
                return oh - 1

        return self.output_height

    def get_max_output_channels(self, id, ow_max, oh_max):
        on_chip_memory = self.memory / 8
        print "Total on-chip memory = {0}".format(on_chip_memory)
        print "Compute Config = {0}".format(self.compute_config)
        # memory_per_pu = int(floor(float(on_chip_memory) / self.compute_config[2]))
        memory_per_pu = self.compute_config[0] * self.hardware["resources"]["memory_per_bram"] / 8
        print "Memory per PU = {0:,} Bytes".format(memory_per_pu)

        memory_per_output = int(ceil(float(ow_max)/self.compute_config[0])*self.compute_config[0]) * oh_max
        memory_per_input = int(ceil(float(self.input_width)/self.compute_config[0])*self.compute_config[0]) * self.input_height * id

        if memory_per_input > memory_per_pu:
            print "Can't fit input feature map"
            return 1

        od = int(floor(float(memory_per_pu - memory_per_input) / memory_per_output))

        print "Output Channels = {0}".format(od)
        return od

    def smart_force(self, conv):
        # TODO : No sharing of inputs
        penalty = None
        best_ow = None
        best_oh = None
        best_od = None
        best_iw = None
        best_ih = None
        best_id = None

        id = self.input_channels
        od = self.output_channels

        # oh_max = self.get_max_height()
        ow_max = self.get_max_width(id, od, 1)
        print "Max width that can fit in PU  = {0}".format(ow_max)
        oh_max = self.get_max_height(id, od, ow_max)
        print "Max height that can fit in PU = {0}".format(oh_max)

        if ow_max == self.output_width and oh_max == self.output_height:
            print "Can fit entire CONV into FPGA"
            best_iw = self.input_width
            best_ih = self.input_height
            best_id = self.input_channels
            best_ow = self.output_width
            best_oh = self.output_height
            best_od = self.output_channels
            kernel_h_next_layer = 0
            oh = oh_max
        else:
            print "Can't fit entire CONV into FPGA"
            print "Dividing CONV into partitions"
            print "Testing with small partition"

            # Find Kernel Height for next layer
            curr = conv.next_layer
            from network import Convolution, InnerProduct, Pooling, Normalization
            while not (isinstance(curr, Convolution) or
                           isinstance(curr, InnerProduct) or
                           isinstance(curr, Pooling) or
                           isinstance(curr, Normalization) or
                               curr is None):
                curr = curr.next_layer
            # curr.print_layer(self.hardware)
            if curr is None or isinstance(curr, InnerProduct):
                kernel_h_next_layer = 0
            else:
                kernel_h_next_layer = curr.params["kernel_size"] - 1



            ow_max = self.get_max_width(1, 1, kernel_h_next_layer+1)
            print "Max width that can fit in PU  = {0}".format(ow_max)
            oh_max = self.get_max_height(1, 1, ow_max)
            print "Max height that can fit in PU = {0}".format(oh_max)

            if ow_max < self.output_width:
                print "ERROR Cant fit entire Width of output"
                # exit(-1)
            else:
                ow = ow_max



            oh = min(int(ceil(self.output_height / ceil(
                float(self.output_height) / (oh_max - kernel_h_next_layer)))) + kernel_h_next_layer, oh_max)
            print "Using max height of {0}".format(oh)

        print "Need to do redundant computations : {0}".format(kernel_h_next_layer * ow_max)

        # Introduce batches
        num_batches = 1

        # oh += kernel_h_next_layer
        ow = ow_max

        id = 1
        # od = self.get_max_output_channels(id, ow, oh)
        # if (od < 1):
        #     # print "Less than one OD"
        #     # exit(-1)
        #     od = 1

        # od = 1
        iw = (ow - 1) * self.stride_x + self.kernel_width
        ih = (oh - 1) * self.stride_y + self.kernel_height

        input_block = [iw, ih, id, num_batches]
        output_block = [ow, oh, od, num_batches]

        tmp = self.get_penalty_print(input_block, output_block, conv)
        best_ow = ow
        best_oh = oh
        best_od = od
        best_iw = iw
        best_ih = ih
        best_id = 1

        input_block = [best_iw, best_ih, best_id, num_batches]
        output_block = [best_ow, best_oh, best_od, num_batches]

        # exit(-1)

        # print "log ({0}) = {1}".format(oh_max, int(ceil(log(oh_max, 2))))
        # # sys.exit()
        # for oh_step in xrange(int(ceil(log(oh_max, 2)))):
        #     print oh_step, int(ceil(log(oh_max, 2)))
        #     oh = oh_max / (2 ** oh_step)
        #     print oh
        #     # for oh in xrange (math)
        #     ih = (oh - 1) * self.stride_y + self.kernel_height
        #     parallelism = 0
        #     # print "Output height = {0}".format(oh)
        #     for od in xrange(1, 1 + self.output_channels):
        #         for id in xrange(1, 1 + self.input_channels):
        #             # ow = self.get_max_width(id, oh, od)
        #             ow = oh
        #             # if oh < ow:
        #             #     [oh, ow] = [ow, oh]
        #             # ih = (oh - 1) * self.stride_y + self.kernel_height
        #             iw = (ow - 1) * self.stride_x + self.kernel_width
        #             tmp = self.get_penalty([ow, oh, od, iw, ih, id])
        #             curr_parallelism = ow * od * oh
        #             if (tmp is not None and penalty >= tmp and (parallelism < curr_parallelism or (
        #                             parallelism == curr_parallelism and id > best_id))) or penalty is None:
        #                 parallelism = curr_parallelism
        #                 best_ow = ow
        #                 best_oh = oh
        #                 best_od = od
        #                 best_iw = iw
        #                 best_ih = ih
        #                 best_id = id
        #                 penalty = tmp
        #
        # exit(-1)
        return [input_block, output_block]
        # return [1, 1, 1, 1, 1, 1]

    def smart_force_norm(self, norm):
        # TODO : No sharing of inputs
        penalty = None
        best_ow = None
        best_oh = None
        best_od = None
        best_iw = None
        best_ih = None
        best_id = None

        id = self.input_channels
        od = self.output_channels

        # oh_max = self.get_max_height()
        ow_max = self.get_max_width(id, od, 1)
        print "Max width that can fit in PU  = {0}".format(ow_max)
        oh_max = self.get_max_height(id, od, ow_max)
        print "Max height that can fit in PU = {0}".format(oh_max)

        if ow_max == self.output_width and oh_max == self.output_height:
            print "Can fit entire Norm into FPGA"
            best_iw = self.input_width
            best_ih = self.input_height
            best_id = self.input_channels
            best_ow = self.output_width
            best_oh = self.output_height
            best_od = self.output_channels
            kernel_h_next_layer = 0
            oh = oh_max
        else:
            print "Can't fit entire Norm into FPGA"
            print "Dividing Norm into partitions"
            print "Testing with small partition"

            # Find Kernel Height for next layer
            curr = norm.next_layer
            from network import Convolution, InnerProduct, Pooling, Normalization
            while not (isinstance(curr, Convolution) or
                           isinstance(curr, InnerProduct) or
                           isinstance(curr, Pooling) or
                           isinstance(curr, Normalization) or
                               curr is None):
                curr = curr.next_layer
            # curr.print_layer(self.hardware)
            if curr is None or isinstance(curr, InnerProduct):
                kernel_h_next_layer = 0
            else:
                kernel_h_next_layer = curr.params["kernel_size"] - 1



            ow_max = self.get_max_width(1, 1, kernel_h_next_layer+1)
            print "Max width that can fit in PU  = {0}".format(ow_max)
            print "Kernel Next = {0}".format(kernel_h_next_layer)
            oh_max = self.get_max_height(1, 1, ow_max)
            print "Max height that can fit in PU = {0}".format(oh_max)

            if ow_max < self.output_width:
                print "ERROR Cant fit entire Width of output"
                # exit(-1)
            else:
                ow = ow_max





            # oh = min(int(ceil(self.output_height / ceil(
            #     float(self.output_height) / (oh_max - kernel_h_next_layer)))) + kernel_h_next_layer, oh_max)
            oh = oh_max
            print "Using max height of {0}".format(oh)



        # print "Need to do redundant computations : {0}".format(kernel_h_next_layer * ow_max)

        # Introduce batches
        num_batches = 1

        # oh += kernel_h_next_layer
        ow = ow_max

        id = 1
        # od = self.get_max_output_channels(id, ow, oh)
        # if (od < 1):
        #     # print "Less than one OD"
        #     # exit(-1)
        #     od = 1

        # od = 1
        iw = min(ow  + self.kernel_width  - 1, self.input_width)
        ih = min(oh  + self.kernel_height - 1, self.input_height)

        input_block = [iw, ih, id, num_batches]
        output_block = [ow, oh, od, num_batches]

        print "Input block = {0}\n Output block = {1}".format(input_block, output_block)
        # exit(-1)

        tmp = self.get_penalty_print_norm(input_block, output_block, norm)
        # exit(-1)
        best_ow = ow
        best_oh = oh
        best_od = od
        best_iw = iw
        best_ih = ih
        best_id = 1

        input_block = [best_iw, best_ih, best_id, num_batches]
        output_block = [best_ow, best_oh, best_od, num_batches]

        # exit(-1)

        # print "log ({0}) = {1}".format(oh_max, int(ceil(log(oh_max, 2))))
        # # sys.exit()
        # for oh_step in xrange(int(ceil(log(oh_max, 2)))):
        #     print oh_step, int(ceil(log(oh_max, 2)))
        #     oh = oh_max / (2 ** oh_step)
        #     print oh
        #     # for oh in xrange (math)
        #     ih = (oh - 1) * self.stride_y + self.kernel_height
        #     parallelism = 0
        #     # print "Output height = {0}".format(oh)
        #     for od in xrange(1, 1 + self.output_channels):
        #         for id in xrange(1, 1 + self.input_channels):
        #             # ow = self.get_max_width(id, oh, od)
        #             ow = oh
        #             # if oh < ow:
        #             #     [oh, ow] = [ow, oh]
        #             # ih = (oh - 1) * self.stride_y + self.kernel_height
        #             iw = (ow - 1) * self.stride_x + self.kernel_width
        #             tmp = self.get_penalty([ow, oh, od, iw, ih, id])
        #             curr_parallelism = ow * od * oh
        #             if (tmp is not None and penalty >= tmp and (parallelism < curr_parallelism or (
        #                             parallelism == curr_parallelism and id > best_id))) or penalty is None:
        #                 parallelism = curr_parallelism
        #                 best_ow = ow
        #                 best_oh = oh
        #                 best_od = od
        #                 best_iw = iw
        #                 best_ih = ih
        #                 best_id = id
        #                 penalty = tmp
        #
        # exit(-1)
        return [input_block, output_block]
        # return [1, 1, 1, 1, 1, 1]

    # def brute_force(self):
    #     penalty = None
    #     best_ow = None
    #     best_oh = None
    #     best_od = None
    #     best_id = None
    #     for ow in xrange(1, 1 + self.output_width):
    #         print ow
    #         for oh in xrange(1, 1 + self.output_height):
    #             for od in xrange(1, 1 + self.output_channels):
    #                 for id in xrange(1, 1 + self.input_channels):
    #                     tmp = self.get_penalty([ow, oh, od, id])
    #                     if ((tmp is not None and penalty > tmp) or penalty is None):
    #                         best_ow = ow
    #                         best_oh = oh
    #                         best_od = od
    #                         best_id = id
    #                         penalty = tmp
    #     return [best_ow, best_oh, best_od, best_id]

    # def get_penalty(self, config):
    #     # [bo_w, bo_h, bo_d, bi_d] = config
    #     [bo_w, bo_h, bo_d, x, y, bi_d] = config
    #     iw = self.input_width
    #     ih = self.input_height
    #     ni = self.input_channels
    #     no = self.output_channels
    #     kw = self.kernel_width
    #     kh = self.kernel_height
    #     ow = self.output_width
    #     oh = self.output_height
    #     iw += 2 * self.pad_x
    #
    #     stride_h = self.stride_y
    #     stride_w = self.stride_x
    #
    #     compute_config = self.compute_config
    #     # print "Compute config = {0}".format(self.compute_config)
    #
    #     # print "Input FM width   = {0}".format(iw)
    #     # print "Input FM height  = {0}".format(ih)
    #     # print "Input FM         = {0}".format(ni)
    #     # print "Kernel Width     = {0}".format(kw)
    #     # print "Kernel height    = {0}".format(kh)
    #     # print "Output height    = {0}".format(ow)
    #     # print "Output width     = {0}".format(oh)
    #     # print "Output FM        = {0}".format(no)
    #
    #     # print
    #     # print "Partitioning Input data into sub-sets"
    #
    #     on_chip_memory = self.memory
    #     # print "On-chip Memory = {0}".format(on_chip_memory)
    #
    #     output_ribbon = [bo_w, bo_h, bo_d]
    #     # input_ribbon = [output_ribbon[0] + kw - 1, output_ribbon[1] + kh - 1, bi_d]
    #     input_ribbon = [(output_ribbon[0] - 1) * stride_w + kw, (output_ribbon[1] - 1) * stride_h + kh, bi_d]
    #     w_steps = int(ceil(float(ow) / output_ribbon[0]))
    #     h_steps = int(ceil(float(oh) / output_ribbon[1]))
    #     od_steps = int(ceil(float(no) / output_ribbon[2]))
    #     id_steps = int(ceil(float(ni) / input_ribbon[2]))
    #
    #     # print "Input  Block size  = {0} x {1} x {2}".format(input_ribbon[0], input_ribbon[1], input_ribbon[2])
    #     # print "Input  Num Blocks  = {0} x {1} x {2}".format(w_steps, h_steps, id_steps)
    #     # print "Output Block size  = {0} x {1} x {2}".format(output_ribbon[0], output_ribbon[1], output_ribbon[2])
    #     # print "Output Num Blocks  = {0} x {1} x {2}".format(w_steps, h_steps, od_steps)
    #
    #     # print "Weight blocks      = {0} x {1} x {2} x {3}".format(kw, kh, input_ribbon[2], output_ribbon[2])
    #
    #     memory_input = input_ribbon[0] * input_ribbon[1] * input_ribbon[2]
    #     memory_weight = kw * kh * input_ribbon[2] * output_ribbon[2]
    #     memory_output = on_chip_memory - memory_input - memory_weight
    #
    #     if (memory_output < output_ribbon[0] * output_ribbon[1] * output_ribbon[2]):
    #         # print "Error:Memory size < output"
    #         return None
    #
    #     # print
    #     # print "Parallelism          = {0:,}".format(output_ribbon[0] * output_ribbon[1] * output_ribbon[2])
    #     # print "Memory for input     = {0:,}".format(memory_input)
    #     # print "Memory for weights   = {0:,}".format(memory_weight)
    #     # print "Memory for outputs   = {0:,}".format(memory_output)
    #
    #     penalty = 0
    #     total_weight_accesses = 0
    #     total_partial_output_accesses = 0
    #     total_input_accesses = 0
    #
    #     bi_w = input_ribbon[0]
    #     bi_h = input_ribbon[1]
    #     bi_d = input_ribbon[2]
    #
    #     bo_w = output_ribbon[0]
    #     bo_h = output_ribbon[1]
    #     bo_d = output_ribbon[2]
    #
    #     ribbon_penalty = iw * bi_h * bi_d
    #     ribbon_overlap = max(bi_w * (kh - 1 - stride_h) * bi_d, 0)
    #
    #     # print "Ribbon Data = {0}\nRibbon Overlap = {1}".format((h_steps - 1) * ribbon_penalty, (h_steps - 1) * ribbon_overlap)
    #
    #     bottom_ribbon_penalty = ((oh - 1) * stride_h - bo_h * (h_steps - 1) + kh) * iw * bi_d
    #
    #     # print "Bottom ribbon dimensions : {0} x {1} x {2}".format((oh-1)*stride_h - bo_h * (h_steps - 1) + kh, iw, bi_d)
    #
    #     # print "Bottom ribbon penalty = {0}".format(bottom_ribbon_penalty)
    #
    #     partition_input_accesses = max((h_steps - 1) * ribbon_penalty, 0) + bottom_ribbon_penalty \
    #                                - max((h_steps - 1) * ribbon_overlap, 0)
    #     # print "Partition Input accesses = {0}".format(partition_input_accesses)
    #
    #     partition_weight_accesses = kw * kh * ni * no
    #
    #     partition_output_access = max(oh * ow * no - memory_output, 0)
    #     formula_output_penalty = (id_steps - 1) * partition_output_access
    #     # print "Formula Output penalty = {0}".format(formula_output_penalty)
    #     penalty += formula_output_penalty
    #     total_weight_accesses += partition_weight_accesses
    #     total_partial_output_accesses += formula_output_penalty
    #     penalty += partition_weight_accesses
    #
    #     partition_input_overlap = bi_w * bi_h * bi_d
    #     total_input_accesses += (od_steps * partition_input_accesses - (
    #         od_steps - 1) * partition_input_overlap) * id_steps
    #     penalty += (od_steps * partition_input_accesses - (od_steps - 1) * partition_input_overlap) * id_steps
    #
    #     # print
    #     # print "Inputs accessed      = {0:,}".format(total_input_accesses)
    #     # print "Weights accessed     = {0:,}".format(total_weight_accesses)
    #     # print "Outputs accessed     = {0:,}".format(total_partial_output_accesses)
    #     # print "Total DRAM Accesses  = {0:,}".format(penalty)
    #
    #     # print
    #     # print "Total Penalty        = {0:,}".format(penalty)
    #     # actual_compute_cycles = ow * oh * no * kw * kh * ni
    #     # print "Compute Cycles       = {0:,}".format(actual_compute_cycles)
    #     return penalty

    def get_penalty_print(self, input_block, output_block, conv):

        [bi_w, bi_h, bi_d, num_batch] = input_block
        [bo_w, bo_h, bo_d, num_batch] = output_block

        iw = self.input_width
        ih = self.input_height
        ni = self.input_channels
        no = self.output_channels
        kw = self.kernel_width
        kh = self.kernel_height
        ow = self.output_width
        oh = self.output_height
        iw += 2 * self.pad_x

        print "*" * 50
        print "Getting DRAM accesses"
        print "*" * 50

        stride_h = self.stride_y
        stride_w = self.stride_x

        print "Input FM width   = {0}".format(iw)
        print "Input FM height  = {0}".format(ih)
        print "Input FM         = {0}".format(ni)
        print "Kernel Width     = {0}".format(kw)
        print "Kernel height    = {0}".format(kh)
        print "Output width     = {0}".format(oh)
        print "Output height    = {0}".format(ow)
        print "Output FM        = {0}".format(no)

        on_chip_memory = self.memory
        print "On-chip Memory = {0}".format(on_chip_memory)

        output_ribbon = [bo_w, bo_h, bo_d]
        print "output size being processed  = {0} x {1} x {2}".format(output_ribbon[0], output_ribbon[1], num_batch)


        input_ribbon = [(output_ribbon[0] - 1) * stride_w + kw, (output_ribbon[1] - 1) * stride_h + kh, bi_d]
        w_steps = int(ceil(float(ow) / output_ribbon[0]))
        h_steps = int(ceil(float(oh) / output_ribbon[1]))

        id_steps = int(ceil(float(ni) / input_ribbon[2]))

        od_per_batch = int(floor(float(self.compute_config[2]) / num_batch))
        #TODO:Verify
        od_steps = int(ceil(ceil(float(no) / output_ribbon[2]) / float(od_per_batch)))



        print
        print "Partitioning Input data into sub-sets"
        print "Input  Block size  = {0} x {1} x {2} x {3}".format(input_ribbon[0], input_ribbon[1], input_ribbon[2],
                                                                  num_batch)
        print "Input  Num Blocks  = {0} x {1} x {2} x 1".format(w_steps, h_steps, id_steps, num_batch)
        print "Output Block size  = {0} x {1} x {2} x {3}".format(output_ribbon[0], output_ribbon[1], od_per_batch,
                                                                  num_batch)
        print "Output Num Blocks  = {0} x {1} x {2} x 1".format(w_steps, h_steps, od_steps, num_batch)

        print "Weight blocks      = {0} x {1} x {2} x {3}".format(kw, kh, input_ribbon[2], output_ribbon[2])

        # memory_input = input_ribbon[0] * input_ribbon[1] * input_ribbon[2]
        memory_input = 0
        memory_weight = kw * kh * input_ribbon[2] * output_ribbon[2]
        memory_output = on_chip_memory - memory_input - memory_weight

        # if (memory_output < output_ribbon[0] * output_ribbon[1] * output_ribbon[2]):
        #     print "Error:Memory size < output"
        #     return None

        print
        print "Parallelism          = {0:,}".format(output_ribbon[0] * output_ribbon[1] * output_ribbon[2])
        print "Memory for input     = {0:,}".format(memory_input)
        print "Memory for weights   = {0:,}".format(memory_weight)
        print "Memory for outputs   = {0:,}".format(memory_output)

        bi_w = input_ribbon[0]
        bi_h = input_ribbon[1]
        bi_d = input_ribbon[2]

        bo_w = output_ribbon[0]
        bo_h = output_ribbon[1]
        bo_d = output_ribbon[2]

        print "Compute Config = {0}".format(self.compute_config)


        # INPUT ACCESSES
        if bi_w <= self.compute_config[0]:
            partial_input_accesses = int(ceil(float(bi_w) / self.compute_config[0]) * self.compute_config[0]) * \
                                     bi_h * \
                                     bi_d * \
                                     od_steps * \
                                     num_batch
        else:
            partial_input_accesses = bi_w *\
                                     bi_h * \
                                     bi_d * \
                                     od_steps * \
                                     num_batch


        print "{0}, {1}, {2}, {3}, {4}".format(bi_w, bi_h, bi_d, od_steps, num_batch)

        print "Partial Input Accesses = {0}".format(partial_input_accesses)
        total_input_accesses = partial_input_accesses * w_steps * h_steps * id_steps
        # WEIGHT ACCESSES
        # A:
        total_weight_accesses = kw * kh * ni * no * w_steps * h_steps
        # OUTPUT ACCESSES
        # A:
        # partial_output_accesses = int(ceil(float(bo_w) / self.compute_config[0]) * self.compute_config[0]) * \
        #                           bo_h * no * w_steps * h_steps
        partial_output_accesses = 0
        total_output_accesses = (ni - 1) * partial_output_accesses

        penalty = total_input_accesses + total_weight_accesses + total_output_accesses
        # penalty = total_input_accesses# + total_weight_accesses + total_output_accesses

        print
        print "Inputs accessed      = {0:,}".format(total_input_accesses)
        print "Weights accessed     = {0:,}".format(total_weight_accesses)
        print "Outputs accessed     = {0:,}".format(total_output_accesses)
        print "Total DRAM Accesses  = {0:,}".format(penalty)

        print
        print "Total Penalty        = {0:,}".format(penalty)
        actual_compute_cycles = ow * oh * no * kw * kh * ni
        print "Compute Cycles       = {0:,}".format(actual_compute_cycles)


        # exit(-1)
        conv.set_data_partition([bi_w, bi_h, bi_d], [bo_w, bo_h, bo_d])

        bw = min(self.hardware["resources"]["bandwidth"], self.compute_config[0])
        memory_access_cycles = int(ceil(float(penalty) / bw))

        print "Memory Access Cycles = {0}".format(memory_access_cycles)

        total_cycles = conv.get_cycles(self.hardware)

        return penalty

        # if strategy == "A":
        #     print "Strategy A"
        #     # INPUT ACCESSES
        #     # A:
        #     total_input_accesses = partial_input_accesses * id_steps * w_steps * h_steps
        #     # WEIGHT ACCESSES
        #     # A:
        #     total_weight_accesses = kw * kh * ni * no * w_steps * h_steps
        #     # OUTPUT ACCESSES
        #     # A:
        #     partial_output_accesses = int(ceil(float(bo_w) / self.compute_config[0]) * self.compute_config[0]) * \
        #                               bo_h * no * w_steps * h_steps
        #     total_output_accesses = (ni - 1) * partial_output_accesses
        #
        # elif strategy == "B":
        #     print "Strategy B"
        #     # INPUT ACCESSES
        #     # B:
        #     total_input_accesses = partial_input_accesses * id_steps * od_steps * w_steps * h_steps
        #     # WEIGHT ACCESSES
        #     # B:
        #     total_weight_accesses = kw * kh * ni * no * od_steps * w_steps * h_steps
        #     # OUTPUT ACCESSES
        #     # B:
        #     partial_output_accesses = 0
        #     total_output_accesses = (ni - 1) * partial_output_accesses
        #
        # else:
        #     print "Strategy C"
        #     # INPUT ACCESSES
        #     # C:
        #     total_input_accesses = partial_input_accesses * id_steps * od_steps * w_steps * h_steps
        #     # WEIGHT ACCESSES
        #     # C:
        #     total_weight_accesses = kw * kh * ni * no
        #     # OUTPUT ACCESSES
        #     # C:
        #     partial_output_accesses = int(ceil(float(bo_w) / self.compute_config[0]) * self.compute_config[0]) * \
        #                               bo_h * no * w_steps * h_steps
        #     total_output_accesses = (ni - 1) * partial_output_accesses

        # OUTPUT ACCESSES
        # A:
        # partial_output_accesses = int(ceil(float(bo_w) / self.compute_config[0]) * self.compute_config[0]) * \
        #                           bo_h * no * w_steps * h_steps
        # B:
        # partial_output_accesses = 0








    def get_penalty_print_norm(self, input_block, output_block, norm):

        [bi_w, bi_h, bi_d, num_batch] = input_block
        [bo_w, bo_h, bo_d, num_batch] = output_block

        iw = self.input_width
        ih = self.input_height
        ni = self.input_channels
        no = self.output_channels
        kw = self.kernel_width
        kh = self.kernel_height
        ow = self.output_width
        oh = self.output_height
        iw += 2 * self.pad_x

        print "*" * 50
        print "Getting DRAM accesses"
        print "*" * 50

        stride_h = self.stride_y
        stride_w = self.stride_x

        print "Input FM width   = {0}".format(iw)
        print "Input FM height  = {0}".format(ih)
        print "Input FM         = {0}".format(ni)
        print "Kernel Width     = {0}".format(kw)
        print "Kernel height    = {0}".format(kh)
        print "Output width     = {0}".format(oh)
        print "Output height    = {0}".format(ow)
        print "Output FM        = {0}".format(no)

        on_chip_memory = self.memory
        print "On-chip Memory = {0}".format(on_chip_memory)

        output_ribbon = [bo_w, bo_h, bo_d]
        print "output size being processed  = {0} x {1} x {2}".format(output_ribbon[0], output_ribbon[1], num_batch)


        input_ribbon = [bi_w, bi_h, bi_d]
        w_steps = int(ceil(float(ow) / output_ribbon[0]))
        h_steps = int(ceil(float(oh) / output_ribbon[1]))

        id_steps = int(ceil(float(ni) / input_ribbon[2]))

        od_per_batch = int(floor(float(self.compute_config[2]) / num_batch))
        od_steps = int(ceil(ceil(float(no) / od_per_batch)))

        print "Num output FMs = {0}".format(no)
        print "Num PU = {0}".format(output_ribbon[2])

        print
        print "Partitioning Input data into sub-sets"
        print "Input  Block size  = {0} x {1} x {2} x {3}".format(input_ribbon[0], input_ribbon[1], input_ribbon[2],
                                                                  num_batch)
        print "Input  Num Blocks  = {0} x {1} x {2} x 1".format(w_steps, h_steps, id_steps, num_batch)
        print "Output Block size  = {0} x {1} x {2} x {3}".format(output_ribbon[0], output_ribbon[1], od_per_batch,
                                                                  num_batch)
        print "Output Num Blocks  = {0} x {1} x {2} x 1".format(w_steps, h_steps, od_steps, num_batch)

        print "Weight blocks      = {0} x {1} x {2} x {3}".format(kw, kh, input_ribbon[2], output_ribbon[2])

        print "Compute config     = {0}".format(self.compute_config)


        # memory_input = input_ribbon[0] * input_ribbon[1] * input_ribbon[2]
        memory_input = 0
        memory_weight = 0
        memory_output = on_chip_memory - memory_input - memory_weight

        # print "Total Memory = {0}".format(self.hardware["resources"]["memory_per_bram"] * self.compute_config[0] * self.compute_config[2])

        # if (memory_output < output_ribbon[0] * output_ribbon[1] * output_ribbon[2]):
        #     print "Error:Memory size < output"
        #     return None

        # print
        # print "Parallelism          = {0:,}".format(output_ribbon[0] * output_ribbon[1] * output_ribbon[2])
        # print "Memory for input     = {0:,}".format(memory_input)
        # print "Memory for weights   = {0:,}".format(memory_weight)
        # print "Memory for outputs   = {0:,}".format(memory_output)


        bi_w = input_ribbon[0]
        bi_h = input_ribbon[1]
        bi_d = input_ribbon[2]

        bo_w = output_ribbon[0]
        bo_h = output_ribbon[1]
        bo_d = output_ribbon[2]

        print "Compute Config = {0}".format(self.compute_config)


        # INPUT ACCESSES
        if bi_w <= self.compute_config[0]:
            partial_input_accesses = int(ceil(float(bi_w) / self.compute_config[0]) * self.compute_config[0]) * \
                                     bi_h * \
                                     bi_d * \
                                     no
        else:
            partial_input_accesses = bi_w *\
                                     bi_h * \
                                     bi_d * \
                                     no


        print "{0}, {1}, {2}, {3}, {4}".format(bi_w, bi_h, bi_d, od_steps, num_batch)

        print "Partial Input Accesses = {0}".format(partial_input_accesses)
        total_input_accesses = partial_input_accesses * w_steps * h_steps
        print "Total Input Accesses = {0}".format(total_input_accesses)

        # WEIGHT ACCESSES
        # A:
        total_weight_accesses = 0
        # OUTPUT ACCESSES
        # A:
        # partial_output_accesses = int(ceil(float(bo_w) / self.compute_config[0]) * self.compute_config[0]) * \
        #                           bo_h * no * w_steps * h_steps
        partial_output_accesses = 0
        total_output_accesses = (ni - 1) * partial_output_accesses

        penalty = total_input_accesses + total_weight_accesses + total_output_accesses
        # penalty = total_input_accesses# + total_weight_accesses + total_output_accesses

        print
        print "Inputs accessed      = {0:,}".format(total_input_accesses)
        print "Weights accessed     = {0:,}".format(total_weight_accesses)
        print "Outputs accessed     = {0:,}".format(total_output_accesses)
        print "Total DRAM Accesses  = {0:,}".format(penalty)

        actual_compute_cycles = norm.get_cycles(self.hardware)
        print "*" * 50
        print
        print "Total Penalty        = {0:,}".format(penalty)
        print "Compute Cycles       = {0:,}".format(actual_compute_cycles)
        bw = min(self.hardware["resources"]["bandwidth"], self.compute_config[0])
        memory_access_cycles = int(ceil(float(penalty) / bw))

        print "Memory Access Cycles = {0:,}".format(memory_access_cycles)
        # exit(-1)


        # exit(-1)
        # norm.set_data_partition([bi_w, bi_h, bi_d], [bo_w, bo_h, bo_d])



        # total_cycles = norm.get_cycles(self.hardware)

        return penalty

        # if strategy == "A":
        #     print "Strategy A"
        #     # INPUT ACCESSES
        #     # A:
        #     total_input_accesses = partial_input_accesses * id_steps * w_steps * h_steps
        #     # WEIGHT ACCESSES
        #     # A:
        #     total_weight_accesses = kw * kh * ni * no * w_steps * h_steps
        #     # OUTPUT ACCESSES
        #     # A:
        #     partial_output_accesses = int(ceil(float(bo_w) / self.compute_config[0]) * self.compute_config[0]) * \
        #                               bo_h * no * w_steps * h_steps
        #     total_output_accesses = (ni - 1) * partial_output_accesses
        #
        # elif strategy == "B":
        #     print "Strategy B"
        #     # INPUT ACCESSES
        #     # B:
        #     total_input_accesses = partial_input_accesses * id_steps * od_steps * w_steps * h_steps
        #     # WEIGHT ACCESSES
        #     # B:
        #     total_weight_accesses = kw * kh * ni * no * od_steps * w_steps * h_steps
        #     # OUTPUT ACCESSES
        #     # B:
        #     partial_output_accesses = 0
        #     total_output_accesses = (ni - 1) * partial_output_accesses
        #
        # else:
        #     print "Strategy C"
        #     # INPUT ACCESSES
        #     # C:
        #     total_input_accesses = partial_input_accesses * id_steps * od_steps * w_steps * h_steps
        #     # WEIGHT ACCESSES
        #     # C:
        #     total_weight_accesses = kw * kh * ni * no
        #     # OUTPUT ACCESSES
        #     # C:
        #     partial_output_accesses = int(ceil(float(bo_w) / self.compute_config[0]) * self.compute_config[0]) * \
        #                               bo_h * no * w_steps * h_steps
        #     total_output_accesses = (ni - 1) * partial_output_accesses

        # OUTPUT ACCESSES
        # A:
        # partial_output_accesses = int(ceil(float(bo_w) / self.compute_config[0]) * self.compute_config[0]) * \
        #                           bo_h * no * w_steps * h_steps
        # B:
        # partial_output_accesses = 0
