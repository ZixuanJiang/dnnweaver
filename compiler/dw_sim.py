from math import ceil, sqrt, floor
import sys
import csv
import json
import numpy
from dfg import DFG
from openProtoBuf import readProtoBuf


class Simulator(object):
    def __init__(self, network_json, hardware_json):
        self.hardware = hardware_json
        if "latency" not in self.hardware["resources"]:
            self.hardware["resources"]["latency"] = 40
        self.layers = {}
        self.create_graph_nodes(network_json)
        self.head = self.tail = None
        self.connect_graph_nodes()
        self.name = network_json["name"]
        self.output_dir = "./output/"
        self.network = network_json

    def initialize_network(self):
        self.layers = {}
        self.head = self.tail = None
        self.create_graph_nodes(self.network)
        self.connect_graph_nodes()
        self.combine_layers()

    def get_config_efficiency(self):
        cycle_count = 0
        ideal_cycle_count = 0
        config = self.hardware["config"]

        curr = self.head.layers[0]
        # self.print_graph_nodes()

        if config[0] == None or config[1] == None or config[2] == None or config[3] == None:
            return None

        while curr is not None:
            # curr.print_layer(self.hardware)
            if isinstance(curr, DataIn) or isinstance(curr, DataOut):
                # if isinstance(curr, DataIn):
                # if not isinstance(curr, InnerProduct):
                curr = curr.next_layer
                continue

            cycle_count += curr.get_cycles(self.hardware)
            ideal_cycle_count += curr.get_ideal_cycles(self.hardware)


            curr = curr.next_layer
        efficiency = float(ideal_cycle_count) / cycle_count

        efficiency *= config[3]

        return efficiency

    def print_hardware_config(self):
        print "  Hardware name: \t%s" % self.hardware["name"]
        print "  BRAM capacity: \t%d KB" % (self.hardware["resources"]["bram_capacity"] / 1024)
        print "  # PEs: \t\t%d" % self.hardware["resources"]["macs"]
        print "  PEs per PU: \t\t%d" % self.hardware["resources"]["pes_per_pu"]
        print "  # PUs: \t\t%d" % self.hardware["resources"]["num_pus"]
        print "  Num input images: \t%d" % self.hardware["resources"]["num_pus"]
        print "  Bandwidth: \t\t%d" % self.hardware["resources"]["bandwidth"] + " Bytes per Cycle"
        print "  Ports: \t\t%d" % self.hardware["resources"]["ports"]

    def create_graph_nodes(self, network_json):
        for layer in network_json["layers"]:
            layer["type"] = str(layer["type"]).lower()
            if layer["type"] == "input" or layer["type"] == "data":
                self.layers[layer["name"]] = DataIn(layer)
            elif layer["type"] == "convolution":
                self.layers[layer["name"]] = Convolution(layer)
            elif layer["type"] == "innerproduct":
                self.layers[layer["name"]] = InnerProduct(layer)
            elif layer["type"] == "activation" or layer["type"] == "relu":
                self.layers[layer["name"]] = Activation(layer)
            elif layer["type"] == "output" or layer["type"] == "OUTPUT":
                self.layers[layer["name"]] = DataOut(layer)
            elif layer["type"] == "pooling":
                self.layers[layer["name"]] = Pooling(layer)
            elif layer["type"] == "normalization" or layer["type"] == "lrn":
                self.layers[layer["name"]] = Normalization(layer)
                print layer
            else:
                raise TemplateException("Layer type '%s' is not supported." % layer["type"])

    def connect_graph_nodes(self):
        for layer in self.layers:
            if self.layers[layer].params["type"] != "data" and self.layers[layer].params["type"] != "output":
                next_node = self.layers[layer].params["output"]
                # prevNode = self.layers[layer].params["input"]
                self.layers[layer].next_layer = self.layers[next_node]
                self.layers[layer].next_layer.prev_layer = self.layers[layer]
                # self.layers[layer].prev_layer = self.layers[prevNode]

            elif "output" not in self.layers[layer].params:
                self.tail = self.layers[layer]
                # prevNode = self.layers[layer].params["input"]
                # self.layers[layer].prev_layer = self.layers[prevNode]

            elif "input" not in self.layers[layer].params:
                self.head = self.layers[layer]
                next_node = self.layers[layer].params["output"]
                self.layers[layer].next_layer = self.layers[next_node]
                self.layers[layer].next_layer.prev_layer = self.layers[layer]

            else:
                print "Error in layer specification. Check Layer : %s" % layer

        curr = self.head
        while curr is not None:
            curr.set_output_dimensions()
            curr = curr.next_layer

    def print_network_config(self):
        output_csv = self.output_dir + str(self.name) + "_config.csv"

        fc_layer = None
        curr = self.head.layers[0]
        # Find first FC layer
        while curr is not None:
            print curr.params["name"]
            if curr.next_layer.params["type"] == "innerproduct":
                print "Found first innerProduct layer"
                fc_layer = curr
                break
            curr = curr.next_layer

        fc_layer.set_receptive_field([1, 1, 1])

        with open(output_csv, 'wb') as csvfile:
            spam_writer = csv.writer(csvfile, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
            spam_writer.writerow([self.name, ""])
            spam_writer.writerow(
                ["Layer", "Weight Size", "Operations", "Output Dimensions", "Output Size", "Reduced Output Dimensions",
                 "Reduced Output size"])

            curr = self.head
            while curr is not None:
                for layer in curr.layers:
                    spam_writer.writerow(layer.print_config(self.hardware))
                curr = curr.next_layer

            spam_writer.writerow(["", "", ""])
            spam_writer.writerow(["", "", ""])
            spam_writer.writerow(["", "", ""])

    def print_graph_nodes(self):
        curr = self.head
        while curr is not None:
            curr.print_layer(self.hardware)

            ####
            # supported_bram_depth = self.hardware["resources"]["max_bram_depth"] / (
            #             8 * self.hardware["data"]["bytes_per_element"])
            # if supported_bram_depth < curr.get_output_buffer_depth(self.hardware):
            # print "Warning - BRAM depth required exceeds maximum available depth"
            # depth_per_channel = curr.get_output_buffer_depth(self.hardware)/curr.params["channels"]
            # max_channels = int(floor(supported_bram_depth / depth_per_channel))
            # print u'BRAMs can support upto {0} channels'.format(max_channels)
            # sys.exit(0)
            curr = curr.next_layer

    def combine_layers(self):
        curr = self.head
        new = MacroNode(curr)
        self.head = new
        curr = curr.next_layer
        while curr.next_layer is not None:
            assert isinstance(self.head, MacroNode)
            print curr.params["type"]
            new.next_layer = MacroNode(curr)
            new = new.next_layer
            curr = curr.next_layer
            while curr.next_layer is not None and \
                    not (str(curr.params["type"]).lower() == "convolution" or
                                 str(curr.params["type"]).lower() == "innerproduct" or
                                 str(curr.params["type"]).lower() == "normalization" or
                                 str(curr.params["type"]).lower() == "lrn" or
                         # str(curr.params["type"]).lower() == "pooling" or
                             False):
                print '  ' + curr.params["type"]
                new.add_layer(curr)
                curr = curr.next_layer
        new.next_layer = MacroNode(curr)
        assert isinstance(self.head, MacroNode)

    def get_best_config(self):

        # curr = self.head
        # min_width = None
        # min_height = None
        # while curr is not None:
        #     layer = curr.layers[0]
        #     if isinstance(layer, Convolution):
        #         # print "Conv Layer - {0}".format(curr.layers[0].params["name"])
        #         od = layer.get_output_dimensions()
        #         if min_width == None or min_width > od[0]:
        #             min_width = od[0]
        #         if min_height == None or min_height > od[1]:
        #             min_height = od[1]
        #     curr = curr.next_layer
        # print "Minimum Width = {0}".format(min_width)
        # print "Minimum Height = {0}".format(min_height)

        max_num_bram = self.hardware["resources"]["num_bram"]
        max_num_macs = self.hardware["resources"]["num_macs"]

        max_kernel_size = 0
        curr = self.head.layers[0]
        while curr is not None:
            if isinstance(curr, Convolution):
                max_kernel_size = max(max_kernel_size, curr.params["kernel_size"])
            curr = curr.next_layer

        print "Max kernel size = {0}".format(max_kernel_size)
        max_kernel_storage = max_kernel_size * max_kernel_size * self.hardware["data"]["bytes_per_weight"]

        if max_kernel_storage > 500:
            bram_conv = int(ceil(float(max_kernel_storage) / self.hardware["resources"]["memory_per_bram"]))
        else:
            bram_conv = 0

        if bram_conv > max_num_bram:
            print "Error : Can not fit Conv Weights in FPGA"
            exit(-1)

        prev_output_size = 0
        best_pes_per_pu = None
        best_cycles_per_image = None
        best_num_pus = None
        for pes_per_pu in range(7, min(max_num_macs, max_num_bram) + 1):
            # for pes_per_pu in range(8, 9):
            # print pes_per_pu
            curr = self.head
            max_buffer_size = 0
            self.hardware["config"] = [pes_per_pu, 1, 1, 1]
            while curr is not None:
                assert isinstance(curr, MacroNode)
                output_size = curr.layers[-1].get_output_size(self.hardware)
                output_dim = curr.layers[-1].get_output_dimensions()
                # print "Output Dimensions = {0}".format(output_dim)
                max_buffer_size = max(max_buffer_size, prev_output_size + output_size)
                # print "Max buffer size = {0}".format(max_buffer_size)
                prev_output_size = output_size
                curr = curr.next_layer

            bram_per_PE = int(ceil(float(self.hardware["resources"]["num_bram"]) / pes_per_pu))

            total_bram_capacity = pes_per_pu * self.hardware["resources"]["memory_per_bram"] / 8 * bram_per_PE
            batch_size = int(floor(float(total_bram_capacity) / max_buffer_size))
            batch_size = min(batch_size, int(floor(float(max_num_macs) / (pes_per_pu + 2))))
            if batch_size < 1:
                continue
            else:
                total_macs = pes_per_pu * batch_size
                # if (total_macs > min(max_num_macs, max_num_bram)):
                if (total_macs > min(max_num_macs, max_num_bram)):
                    batch_size = min(max_num_macs, max_num_bram) / pes_per_pu

                # print "Total Macs used = {0}".format(pes_per_pu * batch_size)

                # Check for BRAMs
                bram_per_batch = int(floor(float(max_num_bram) / batch_size))
                bram_per_PE = int(floor(float(bram_per_batch) / pes_per_pu))

                config = [pes_per_pu, 1, 1, batch_size]
                self.hardware["config"] = config
                self.hardware["resources"]["pes_per_pu"] = pes_per_pu
                self.hardware["resources"]["num_pus"] = batch_size
                curr = self.head
                assert isinstance(self.head, MacroNode)
                total_cycles = 0
                data_cycles = 0
                while curr is not None:
                    assert isinstance(curr, MacroNode)
                    total_cycles += curr.get_cycles(self.hardware)
                    data_cycles += curr.get_memory_access_cycles(self.hardware)
                    curr = curr.next_layer
                cycles_per_image = total_cycles / batch_size
                if best_pes_per_pu is None or best_cycles_per_image > cycles_per_image or (
                                best_cycles_per_image == cycles_per_image and best_pes_per_pu < pes_per_pu):
                    best_cycles_per_image = cycles_per_image
                    best_pes_per_pu = pes_per_pu
                    best_num_pus = batch_size
                    # print 'Best Config: PES_PER_PU = {0}, NUM_PUS = {1}'.format(best_pes_per_pu, best_num_pus)
                    # print 'Best Cycles per image = {0}'.format(best_cycles_per_image)

        # return best_pes_per_pu

        self.hardware["config"] = [best_pes_per_pu, 1, 1, best_num_pus]
        print "Config = {0}".format(self.hardware["config"])
        #print "Efficiency = {0}".format(self.get_config_efficiency())
        # exit(-1)

        if best_pes_per_pu is None or self.get_config_efficiency() < 0.7:
            print "Batch size is less than 1"
            print "Can't fit entire Network on the FPGA"
            print "Dividing the network into batches"

            # print "Getting Best PEs per PU first"

            # for pes_per_pu in range(7, min(max_num_macs, max_num_bram) + 1):
            for pes_per_pu in range(7, 20 + 1):
                # for pes_per_pu in range(8, 9):
                curr = self.head
                max_buffer_size = 0
                self.hardware["config"] = [pes_per_pu, 1, 1, 1]
                while curr is not None:
                    assert isinstance(curr, MacroNode)
                    output_size = curr.layers[-1].get_output_size(self.hardware)
                    output_dim = curr.layers[-1].get_output_dimensions()
                    # print "Output Dimensions = {0}".format(output_dim)
                    max_buffer_size = max(max_buffer_size, prev_output_size + output_size)
                    # print "Max buffer size = {0}".format(max_buffer_size)
                    prev_output_size = output_size
                    curr = curr.next_layer

                batch_size = 1
                # num_pus = min(max_num_macs, max_num_bram) / (pes_per_pu + bram_conv)
                num_pus = min(int(floor(float(max_num_bram) / (pes_per_pu + bram_conv))),
                              int(floor(float(max_num_macs) / (pes_per_pu + 2))))

                if num_pus < 1:
                    continue
                total_macs = pes_per_pu * batch_size
                # print "Checking configuration : {0} x {1}".format(pes_per_pu, num_pus)
                # if (total_macs > min(max_num_macs, max_num_bram)):
                # batch_size = min(max_num_macs, max_num_bram) / pes_per_pu

                # Check for BRAMs
                bram_per_batch = int(floor(float(max_num_bram) / batch_size))
                bram_per_PE = int(floor(float(bram_per_batch) / pes_per_pu))

                config = [pes_per_pu, 1, num_pus, 1]
                # print "Using config = {0}".format(config)
                self.hardware["config"] = config
                # self.hardware["resources"]["pes_per_pu"] = pes_per_pu
                # self.hardware["resources"]["num_pus"] = batch_size
                curr = self.head
                assert isinstance(self.head, MacroNode)
                total_cycles = 0
                data_cycles = 0
                while curr is not None:
                    assert isinstance(curr, MacroNode)
                    total_cycles += curr.get_cycles(self.hardware)
                    data_cycles += curr.get_memory_access_cycles(self.hardware)
                    curr = curr.next_layer
                cycles_per_image = total_cycles / batch_size
                if best_pes_per_pu is None or best_cycles_per_image > cycles_per_image or (
                                best_cycles_per_image == cycles_per_image and best_pes_per_pu < pes_per_pu):
                    best_cycles_per_image = cycles_per_image
                    best_pes_per_pu = pes_per_pu
                    best_num_pus = num_pus
                    # print 'Best Config: PES_PER_PU = {0}, NUM_PUS = {1}'.format(best_pes_per_pu, best_num_pus)
                    # print 'Best Cycles per image = {0}'.format(best_cycles_per_image)
                self.hardware["config"] = [best_pes_per_pu, 1, best_num_pus, 1]
                # print "Found best Compute config for Network = {0} x 1 x {1} x 1".format(best_pes_per_pu, best_num_pus)
                # print

            print "*" * 50
            print "Getting best Data partition"
            print "*" * 50

            self.hardware["config"] = [best_pes_per_pu, 1, best_num_pus, 1]
            print "Best config  = {0}".format(self.hardware["config"])
            self.create_data_partitions()

            print "Getting best batch size for inner-product"
            # exit(-1)

            curr = self.head.layers[0]
            ip_cycles = 0
            ip_batch = 1

            return [best_pes_per_pu, 1, best_num_pus, 1]

        else:
            self.hardware["config"] = [best_pes_per_pu, 1, 1, best_num_pus]
            return [best_pes_per_pu, 1, 1, best_num_pus]

    def get_best_config_large(self):

        # curr = self.head
        # min_width = None
        # min_height = None
        # while curr is not None:
        #     layer = curr.layers[0]
        #     if isinstance(layer, Convolution):
        #         # print "Conv Layer - {0}".format(curr.layers[0].params["name"])
        #         od = layer.get_output_dimensions()
        #         if min_width == None or min_width > od[0]:
        #             min_width = od[0]
        #         if min_height == None or min_height > od[1]:
        #             min_height = od[1]
        #     curr = curr.next_layer
        # print "Minimum Width = {0}".format(min_width)
        # print "Minimum Height = {0}".format(min_height)

        max_num_bram = self.hardware["resources"]["num_bram"]
        max_num_macs = self.hardware["resources"]["num_macs"]

        max_kernel_size = 0
        curr = self.head.layers[0]
        while curr is not None:
            if isinstance(curr, Convolution):
                max_kernel_size = max(max_kernel_size, curr.params["kernel_size"])
            curr = curr.next_layer

        print "Max kernel size = {0}".format(max_kernel_size)
        max_kernel_storage = max_kernel_size * max_kernel_size * self.hardware["data"]["bytes_per_weight"]

        if max_kernel_storage > 500:
            bram_conv = int(ceil(float(max_kernel_storage) / self.hardware["resources"]["memory_per_bram"]))
        else:
            bram_conv = 0

        print "Bram allocated for Conv Weights = {0}".format(bram_conv)

        if bram_conv > max_num_bram:
            print "Error : Can not fit Conv Weights in FPGA"
            exit(-1)

        prev_output_size = 0
        best_pes_per_pu = None
        best_cycles_per_image = None
        best_num_pus = None

        best_efficiency = None

        if best_pes_per_pu is None or self.get_config_efficiency() < 0.7:
            print "Batch size is less than 1"
            print "Can't fit entire Network on the FPGA"
            print "Dividing the network into batches"

            # print "Getting Best PEs per PU first"

            # for pes_per_pu in range(7, min(max_num_macs, max_num_bram) + 1):
            for pes_per_pu in range(7, 20 + 1):
                # for pes_per_pu in range(8, 9):
                curr = self.head
                max_buffer_size = 0
                self.hardware["config"] = [pes_per_pu, 1, 1, 1]
                while curr is not None:
                    assert isinstance(curr, MacroNode)
                    output_size = curr.layers[-1].get_output_size(self.hardware)
                    output_dim = curr.layers[-1].get_output_dimensions()
                    # print "Output Dimensions = {0}".format(output_dim)
                    max_buffer_size = max(max_buffer_size, prev_output_size + output_size)
                    # print "Max buffer size = {0}".format(max_buffer_size)
                    prev_output_size = output_size
                    curr = curr.next_layer

                batch_size = 1
                # num_pus = min(max_num_macs, max_num_bram) / (pes_per_pu + bram_conv)
                num_pus = min(int(floor(float(max_num_bram) / (pes_per_pu + bram_conv))),
                              int(floor(float(max_num_macs) / (pes_per_pu + 2))))

                if num_pus < 1:
                    continue
                total_macs = pes_per_pu * batch_size
                # print "Checking configuration : {0} x {1}".format(pes_per_pu, num_pus)
                # if (total_macs > min(max_num_macs, max_num_bram)):
                # batch_size = min(max_num_macs, max_num_bram) / pes_per_pu

                # Check for BRAMs
                bram_per_batch = int(floor(float(max_num_bram) / batch_size))
                bram_per_PE = int(floor(float(bram_per_batch) / pes_per_pu))

                config = [pes_per_pu, 1, num_pus, 1]
                # print "Using config = {0}".format(config)
                self.hardware["config"] = config
                # self.hardware["resources"]["pes_per_pu"] = pes_per_pu
                # self.hardware["resources"]["num_pus"] = batch_size
                curr = self.head
                assert isinstance(self.head, MacroNode)
                total_cycles = 0
                data_cycles = 0
                # while curr is not None:
                #     assert isinstance(curr, MacroNode)
                #     total_cycles += curr.get_cycles(self.hardware)
                #     data_cycles += curr.get_memory_access_cycles(self.hardware)
                #     curr = curr.next_layer
                # cycles_per_image = total_cycles / batch_size
                # if best_pes_per_pu is None or best_cycles_per_image > cycles_per_image or (
                #                 best_cycles_per_image == cycles_per_image and best_pes_per_pu < pes_per_pu):
                #     best_cycles_per_image = cycles_per_image
                #     best_pes_per_pu = pes_per_pu
                #     best_num_pus = num_pus
                e = self.get_config_efficiency()

                print "config = {0}x{1} Efficiency = {2}".format(pes_per_pu, num_pus, e)

                if best_efficiency is None or best_efficiency < e:
                    best_efficiency = e
                    best_pes_per_pu = pes_per_pu
                    best_num_pus = num_pus




                    # print 'Best Config: PES_PER_PU = {0}, NUM_PUS = {1}'.format(best_pes_per_pu, best_num_pus)
                    # print 'Best Cycles per image = {0}'.format(best_cycles_per_image)
                self.hardware["config"] = [best_pes_per_pu, 1, best_num_pus, 1]
                # print "Found best Compute config for Network = {0} x 1 x {1} x 1".format(best_pes_per_pu, best_num_pus)
                # print

            print "*" * 50
            print "Getting best Data partition"
            print "*" * 50

            self.hardware["config"] = [best_pes_per_pu, 1, best_num_pus, 1]
            print "Best config  = {0}".format(self.hardware["config"])
            self.create_data_partitions()

            print "Getting best batch size for inner-product"
            # exit(-1)

            curr = self.head.layers[0]
            ip_cycles = 0
            ip_batch = 1

            return [best_pes_per_pu, 1, best_num_pus, 1]

        else:
            self.hardware["config"] = [best_pes_per_pu, 1, 1, best_num_pus]
            return [best_pes_per_pu, 1, 1, best_num_pus]

    def get_network_ops(self):
        curr = self.head
        assert isinstance(self.head, MacroNode)
        total_ops = 0
        while curr is not None:
            assert isinstance(curr, MacroNode)
            total_ops += curr.get_ops(self.hardware)
            print "Ops = {0}".format(total_ops)
            curr = curr.next_layer
        return total_ops

    def simulate(self):
        print "*" * 50
        print "FPGA Platform - {0}".format(str(self.hardware["resources"]["fpga"]).upper())

        # self.hardware["config"] = [8, 8, 3]
        print "*" * 50
        print "Simulation Results:"
        print

        self.hardware["config"] = self.get_best_config()

        config = self.hardware["config"]
        print "*" * 50
        print "Design Configuration - {0} x {1} x {2} x {3}".format(config[0], config[1], config[2], config[3])
        print "Total Maccs used     - {0}".format(config[0] * config[1] * config[2] * config[3])
        print "*" * 50

        curr = self.head
        assert isinstance(self.head, MacroNode)
        total_cycles = 0
        data_cycles = 0
        while curr is not None:
            assert isinstance(curr, MacroNode)
            total_cycles += curr.get_cycles(self.hardware)
            #print curr.name, curr.get_cycles(self.hardware)
            data_cycles += curr.get_memory_access_cycles(self.hardware)
            curr = curr.next_layer
        #
        print 'Total cycles required = {0}'.format(str(total_cycles))
        print 'Data Access cycles    = {0}'.format(str(data_cycles))
        print 'Batch Size            = {0}'.format(str(self.hardware["config"][3]))
        cycles_per_image = total_cycles / self.hardware["config"][3]
        print 'Mean cycles per input = {0}'.format(str(cycles_per_image))
        images_per_second = float(self.hardware["resources"]["frequency"]) / cycles_per_image
        print 'Images per second     = {0}'.format(images_per_second)
        print

        return self.hardware["config"]

    def get_cycles(self):
        curr = self.head
        assert isinstance(self.head, MacroNode)
        total_cycles = 0
        data_cycles = 0
        while curr is not None:
            assert isinstance(curr, MacroNode)
            if isinstance(curr.layers[0], DataIn) or isinstance(curr.layers[0], DataOut):
                curr = curr.next_layer
                continue
            total_cycles += curr.get_cycles(self.hardware)
            print curr.name, curr.get_cycles(self.hardware)
            data_cycles += curr.get_memory_access_cycles(self.hardware)
            curr = curr.next_layer

        return total_cycles

    def get_latency(self):
        cycles = self.get_cycles()
        freq = self.hardware["resources"]["frequency"]
        time_in_ms = float(cycles) * 1000 / freq
        return time_in_ms

    def create_data_partitions(self):
        print "*" * 50
        print "Partitioning Data to fit on-chip"
        print "*" * 50
        curr = self.head.next_layer
        output_csv = self.output_dir + str(self.name) + "_" + str(self.hardware["resources"]["fpga"]) + "_schedule.csv"
        # partition = {}
        with open(output_csv, 'wb') as csvfile:
            spam_writer = csv.writer(csvfile, delimiter=',',
                                     quotechar='|', quoting=csv.QUOTE_MINIMAL)
            spam_writer.writerow([self.name, ""])
            spam_writer.writerow(
                ["Layer", "Input Dimensions", "Input Block", "Output Dimensions", "Output Block", "Data Accesses"])
            total_penalty = 0
            while curr is not None:
                # curr.print_layer(self.hardware)
                dfg = DFG(curr.layers[0], self.hardware)
                if isinstance(curr.layers[0], Convolution) or isinstance(curr.layers[0], Normalization):
                    [config_input, config_output, penalty] = dfg.schedule(curr.layers[0])
                else:
                    curr = curr.next_layer
                    continue
                conv = curr.layers[0]
                # in_dim = conv.get_input_dimensions()
                # out_dim = conv.get_output_dimensions()
                # partition[conv] = [[config[3], config[4], config[5]], [config[0], config[1], config[2]]]
                # in_dim_text = "{0} x {1} x {2}".format(in_dim[0], in_dim[1], in_dim[2])
                # out_dim_text = "{0} x {1} x {2}".format(out_dim[0], out_dim[1], out_dim[2])
                # print "Input Dimensions = {0};\t Output Dimensions = {1}".format(in_dim_text, out_dim_text)
                # config_input = "{0} x {1} x {2}".format(config_input[0], config_input[1], config_input[2])
                # config_output = "{0} x {1} x {2}".format(config_output[0], config_output[1], config_output[2])
                # conv.set_data_partition(in_dim, out_dim)
                # spam_writer.writerow([curr.name, in_dim_text, config_input, out_dim_text, config_output, penalty])
                total_penalty += penalty
                curr = curr.next_layer
                # spam_writer.writerow(["", "", "", "", "", total_penalty])
                # spam_writer.writerow(["", ""])
                # return partition

    ###############################################

##############################################################################################
##############################################################################################

class MacroNode(object):
    def __init__(self, l):
        assert isinstance(l, LayerNode)
        self.layers = []
        self.layers.append(l)
        self.name = l.params["name"]
        self.num_layers = 1
        self.next_layer = None
        self.prev_layer = None
        self.params = {"channels": l.params["input_channels"]}

    def add_layer(self, l):
        assert isinstance(l, LayerNode)
        self.layers.append(l)
        self.name = self.name + ' + ' + l.params["name"]

    def print_config(self, hardware):
        for layer in self.layers:
            layer.print_config(hardware)

    def print_layer(self, hardware):
        print "---------------------"
        print "---MACRO NODE--------"
        print "---------------------"
        print "Macro Node : {0}".format(str(self.name))
        for layer in self.layers:
            layer.print_layer(hardware)
            # print "{0} : {1}".format(str(self.name).ljust(30), str(self.get_cycles(hardware)))
            # print "Operations = {0}".format(str(self.get_ops(hardware)))

    def get_output_buffer_depth(self, hardware):
        return self.layers[-1].get_output_buffer_depth(hardware)

    def get_cycles(self, hardware):
        cycles = 0
        for layer in self.layers:
            # cycles = max(cycles, layer.get_cycles(hardware))
            cycles += layer.get_cycles(hardware)
        return cycles  # + self.layers[-1].get_memory_access_cycles(hardware)

    def get_compute_cycles(self, hardware):
        compute_cycles = 0
        for layer in self.layers:
            # cycles = max(cycles, layer.get_cycles(hardware))
            compute_cycles += layer.get_compute_cycles(hardware)
        return compute_cycles  # + self.layers[-1].get_memory_access_cycles(hardware)

    def get_ops(self, hardware):
        ops = 0
        # print self.name
        for layer in self.layers:
            ops += layer.get_ops(hardware)
            # print "OPS = {1} : {0}".format(layer.get_ops(hardware), layer.params["name"])
        # print "total = {0}".format(ops)
        return ops

    def get_memory_access_cycles(self, hardware):
        data_cycles = 0
        for layer in self.layers:
            # cycles = max(cycles, layer.get_cycles(hardware))
            data_cycles += layer.get_memory_access_cycles(hardware)
        return data_cycles  # + self.layers[-1].get_memory_access_cycles(hardware)

    def get_output_buffer_size(self, hardware):
        return self.layers[-1].get_output_buffer_size(hardware)

    def get_weights_size(self, hardware):
        w = 0
        for l in self.layers:
            w += l.get_weights_size(hardware)
        return w

    def get_conv_weights_size(self, hardware):
        w = 0
        for l in self.layers:
            if (isinstance(l, Convolution)):
                w += l.get_weights_size(hardware)
        return w

    def get_fc_weights_size(self, hardware):
        w = 0
        for l in self.layers:
            if (isinstance(l, InnerProduct)):
                w += l.get_weights_size(hardware)
        return w


class LayerNode(object):
    def __init__(self, layer_params):
        self.params = layer_params
        self.next_layer = None
        self.prev_layer = None
        if "pad" in self.params:
            self.params["pad_x"] = self.params["pad"]
            self.params["pad_y"] = self.params["pad"]
        if "stride" in self.params:
            self.params["stride_x"] = self.params["stride"]
            self.params["stride_y"] = self.params["stride"]

    def get_weights_dimensions(self):
        return [0, 0, 0, 0]

    def get_weights_size(self, hardware):
        dim = self.get_weights_dimensions()
        return dim[0] * dim[1] * dim[2] * dim[3] * hardware["data"]["bytes_per_weight"]

    def get_output_size(self, hardware):
        output_dimensions = self.get_output_dimensions()
        if output_dimensions[0] == 1:
            dim_2 = int(ceil(float(output_dimensions[2]) / hardware["config"][0])) * hardware["config"][0]
            return dim_2 * output_dimensions[1] * output_dimensions[0] * hardware["data"]["bytes_per_element"]
        else:
            dim_0 = int(ceil(float(output_dimensions[0]) / hardware["config"][0])) * hardware["config"][0]
            return dim_0 * output_dimensions[1] * output_dimensions[2] * hardware["data"]["bytes_per_element"]

    # def get_block_weights_dimensions(self, block):
    #     return [0, 0, 0, 0]
    #
    # def get_block_weights_size(self, hardware, block):
    #     dim = self.get_block_weights_dimensions(block)
    #     return dim[0] * dim[1] * dim[2] * dim[3] * hardware["data"]["bytes_per_weight"]
    #
    # def get_block_input_dimensions(self, block):
    #     return [0, 0, 0]
    #
    # def get_block_input_size(self, hardware, block):
    #     dim = self.get_block_weights_dimensions(block)
    #     return dim[0] * dim[1] * dim[2] * hardware["data"]["bytes_per_element"]

    def get_output_elements(self):
        output_dimensions = self.get_output_dimensions()
        return output_dimensions[0] * output_dimensions[1] * output_dimensions[2]

    def get_output_buffer_depth(self, hardware):
        output_dimensions = self.get_output_dimensions()
        if output_dimensions[0] == 1 and output_dimensions[1] == 1:
            return int(ceil(float(output_dimensions[2]) / hardware["resources"]["pes_per_pu"]))
        else:
            return int(ceil(float(output_dimensions[0]) / hardware["resources"]["pes_per_pu"])) * \
                   output_dimensions[1] * output_dimensions[2]

    def get_output_buffer_size(self, hardware):
        output_buffer_depth = self.get_output_buffer_depth(hardware)
        return float(output_buffer_depth) * hardware["resources"]["pes_per_pu"] * hardware["data"][
            "bytes_per_element"] * hardware["resources"]["num_pus"] / 1024

    def get_cycles(self, hardware):
        return self.get_compute_cycles(hardware) + self.get_memory_access_cycles(hardware)

    def get_output_dimensions(self):
        pass

    def get_compute_cycles(self, hardware):
        return 0

    def get_output_buffer_dimensions(self):
        return self.get_output_dimensions()

    def get_memory_access_cycles(self, hardware):
        # output_dimensions = self.get_output_dimensions()
        # supported_BRAM_depth = hardware["resources"]["max_bram_depth"] / (
        #     8 * hardware["data"]["bytes_per_element"])
        # required_BRAM_depth = self.get_output_buffer_depth(hardware)
        #
        #     TODO:SHARED PRIVATE KERNELS
        # if (supported_BRAM_depth < required_BRAM_depth):
        #     print "ERROR, exceeding memory, num_outputs = {0}".format(self.params["input_channels"])
        #     sys.exit(-1)
        #     return 2*int(ceil(ceil((float(output_dimensions[0]) / hardware["resources"]["pes_per_pu"]) *
        #           hardware["resources"]["pes_per_pu"] * output_dimensions[1] * output_dimensions[2]) /
        #           hardware["resources"]["bandwidth"])*hardware["resources"]["num_pus"] *
        #           hardware["data"]["bytes_per_element"])/self.params["input_channels"]
        # else:
        #     return 0
        return 0

    def get_ops(self, hardware):
        return 0

    def get_input_block(self, patch):
        return patch

    def get_reduced_output_dimensions(self):
        if "reduced_output_dimensions" not in self.params:
            self.params["reduced_output_dimensions"] = [1, 1, 1]
        return self.params["reduced_output_dimensions"]

    def get_reduced_output_size(self, hardware):
        dim = self.params["reduced_output_dimensions"]
        return dim[0] * dim[1] * dim[2] * hardware["data"]["bytes_per_element"]

    def print_cycles(self, hardware):
        print '  --Cycles required in this layer:\t{0:,}'.format(self.get_cycles(hardware))
        print '  --Compute Cycles:\t\t\t{0:,}'.format(self.get_compute_cycles(hardware))
        print '  --Memory Cycles:\t\t\t{0:,}'.format(self.get_memory_access_cycles(hardware))

    def print_config(self, hardware):
        print '{0:15} ||  Weight Dim = {1:20} ||  Weights = {2:11,} Bytes ||  Operations = {3:16,} ||  ' \
              'Output Dimensions = {4:17} ||  Output = {5:10,} Bytes ||  Reduced Output Dimensions = {6:12} || ' \
              'Reduced Output Size = {7:12}'.format(self.params["name"], self.get_weights_dimensions(),
                                                    self.get_weights_size(hardware),
                                                    self.get_ops(hardware),
                                                    self.get_output_dimensions(),
                                                    self.get_output_size(hardware),
                                                    self.get_reduced_output_dimensions(),
                                                    self.get_reduced_output_size(hardware))
        od = self.get_output_dimensions()
        od_text = "[{0} * {1} * {2}]".format(od[0], od[1], od[2])
        rod = self.get_reduced_output_dimensions()
        rod_text = "[{0} * {1} * {2}]".format(rod[0], rod[1], rod[2])
        return [self.params["name"], self.get_weights_size(hardware), self.get_ops(hardware), od_text,
                self.get_output_size(hardware), rod_text, self.get_reduced_output_size(hardware)]

    def print_layer(self, hardware):
        print 'Layer {0}:'.format(self.params["type"])
        print '  --Dimensions of Output Data:\t\t{0}'.format(self.get_output_dimensions())

        od = self.get_output_dimensions()
        out_size = od[0] * od[1] * od[2] * hardware["data"]["bytes_per_element"]
        print '  --Size of Output in Bytes:\t\t{0:,} Bytes'.format(out_size)

        print "  --Number of Operations:\t\t{0:,}".format(self.get_ops(hardware))
        print '  --Size of Output Data:\t\t{0:,} elements'.format(self.get_output_elements())
        print '  --Dimensions of Weights:\t\t{0}'.format(self.get_weights_dimensions())
        print '  --Size of Weights:\t\t\t{0} Bytes'.format(
            self.get_weights_size(hardware))
        # print "  --Output buffer depth used:\t\t{0:,}".format(self.get_output_buffer_depth(hardware))
        # print '  --Output buffer size used:\t\t{0} KB'.format(self.get_output_buffer_size(hardware))
        self.print_cycles(hardware)
        print

    def get_ideal_cycles(self, hardware):
        return 0


class DataIn(LayerNode):
    def __init__(self, layer_params):
        super(self.__class__, self).__init__(layer_params)
        self.params["input_channels"] = self.params["output_channels"]

    def set_output_dimensions(self):
        if ("size_x" not in self.params or "size_y" not in self.params) and "size" in self.params:
            self.params["size_x"] = int(ceil(sqrt(self.params["size"])))
            self.params["size_y"] = int(ceil(sqrt(self.params["size"])))
            del (self.params["size"])

    def get_cycles(self, hardware):
        return self.get_memory_access_cycles(hardware)

    def get_output_dimensions(self):
        return [self.params["size_x"], self.params["size_y"], self.params["output_channels"]]

    def get_compute_cycles(self, hardware):
        return 0

    # TODO: CHECK THIS
    def get_memory_access_cycles(self, hardware):
        initial_link_latency = 40  # Latency for read request
        od = self.get_output_dimensions()
        config = hardware["config"]
        total_cycles = initial_link_latency + int(ceil((ceil((float(od[0]) / config[0])) *
                                                        config[0] * od[1] * od[2] *
                                                        hardware["config"][3] * hardware["data"]["bytes_per_element"]) /
                                                       hardware["resources"]["bandwidth"]))
        return total_cycles

        # return int(
        #     ceil(float(self.get_output_elements() * hardware["config"][3]) / hardware["resources"]["bandwidth"])) + \
        #        hardware["resources"]["latency"]

    def get_compute_cycles_batch(self, hardware, batch_size):
        return 0

    def get_cycles_batch(self, hardware, batch_size):
        return 0


class Convolution(LayerNode):
    def __init__(self, layer_params):
        super(self.__class__, self).__init__(layer_params)
        if 'pad_x' not in self.params:
            self.params["pad_x"] = 0
        if 'pad_y' not in self.params:
            self.params["pad_y"] = 0
        if 'stride_x' not in self.params:
            self.params["stride_x"] = 1
        if 'stride_y' not in self.params:
            self.params["stride_y"] = 1
        self.params["group"] = layer_params["group"]

        self.input_partition = None
        self.output_parition = None

        self.memory_accesses = 0

    def print_layer(self, hardware):
        super(self.__class__, self).print_layer(hardware)
        print "CONVOLUTION GROUP = {0}".format(self.params["group"])

    def get_ops(self, hardware):
        od = self.get_output_dimensions()
        input_channels = self.prev_layer.params["input_channels"]
        return od[0] * od[1] * od[2] * (self.params["kernel_size"] * self.params["kernel_size"]) * input_channels / self.params["group"]

    def get_weights_size(self, hardware):
        dim = self.get_weights_dimensions()
        return dim[0]*dim[1]*dim[2]*dim[3]/self.params["group"] * hardware["data"]["bytes_per_weight"]

    def get_compute_cycles(self, hardware):

        if self.input_partition == None:

            # TODO : Add more cycles for Adding feature maps
            # i = self.in_dim
            config = hardware["config"]
            output_dimensions = self.get_output_dimensions()
            d = config[2]
            r = int(ceil(float(output_dimensions[0]) / config[0]))
            # print "Config = {0}".format(config)
            # print "Output Dimensions = {0}".format(output_dimensions)
            # print "Number of blocks per row = {0}".format(r)
            # if r > config[2]:
            #     # print "Convolution Error : Need more compute blocks. Current config - {0}".format(config)
            #     r = config[2]
            r = 1
            d /= r
            c = 1
            # print "Compute {0} x {1} x {2} at a time".format(r * config[0], c * config[1], d)

            num_iterations = int(ceil(float(output_dimensions[0]) / (config[0] * r))) * \
                             int(ceil(float(output_dimensions[1]) / (config[1] * c))) * \
                             int(ceil(float(output_dimensions[2]) / (d))) * \
                             self.params["input_channels"]

            # print "Num of iterations = {0}".format(num_iterations)

            compute_cycles = num_iterations * self.params["kernel_size"] * self.params["kernel_size"]

            # ideal_cycles = (self.params["input_channels"] * output_dimensions[0] * output_dimensions[1] * output_dimensions[
            #     2] * self.params["kernel_size"] * self.params["kernel_size"]) / (config[0] * config[1] * config[2])
            # print "Ideal cycles = {0}\nActual Cycles = {1}\n efficiency = {2}".format(ideal_cycles, compute_cycles, float(
            #     ideal_cycles) / compute_cycles * 100)

            return compute_cycles

        else:
            print "*" * 50
            print "Input  block size = {0}".format(self.input_partition)
            print "Output block size = {0}".format(self.output_parition)
            print "Weight dimenstions = {0}".format(self.get_weights_dimensions())
            input_dimensions = self.prev_layer.get_output_dimensions()
            output_dimensions = self.get_output_dimensions()
            print "Input  Dimensions = {0}".format(input_dimensions)
            print "Output Dimensions = {0}".format(output_dimensions)
            print "*" * 50

            config = hardware["config"]
            print "Current Configuration = {0}".format(config)
            d = config[2]
            c = 1
            r = int(ceil(float(self.output_parition[0]) / config[0]))
            # r = 1
            # if r > d:
            #     # print "Convolution Error : Need more compute blocks. Current config - {0}".format(config)
            #     r = d
            #     d = 1
            # else:
            #     d /= r
            print "Config = {0}".format(config)
            print "Compute {0} x {1} x {2} at a time".format(r * config[0], c * config[1], d)

            num_iterations = int(ceil(float(output_dimensions[0]) / (config[0] * r)) * r) * \
                             int(ceil(float(output_dimensions[1]) / (config[1] * c))) * \
                             int(ceil(float(output_dimensions[2]) / (d))) * \
                             self.params["input_channels"]

            print "Num of iterations = {0}".format(num_iterations)

            compute_cycles = num_iterations * self.params["kernel_size"] * self.params["kernel_size"]

            print "Kernel size = {0}".format(self.params["kernel_size"])

            print "COMPUTE CYCLES = {0}".format(compute_cycles)
            print "COMPUTE CYCLES = {0}".format(
                num_iterations * self.params["kernel_size"] * self.params["kernel_size"])
            print "num_iterations = {0}".format(num_iterations)

            return compute_cycles

            # return int(ceil(float(output_dimensions[0]) / hardware["resources"]["pes_per_pu"]) * output_dimensions[1] *
            #            output_dimensions[2] * (self.params["kernel_size"] ** 2)) * self.params["input_channels"]

    def set_output_dimensions(self):
        prev_layer_params = self.prev_layer.params
        self.params["size_x"] = 1 + (prev_layer_params["size_x"] + self.params["pad_x"] * 2 - self.params[
            "kernel_size"]) / (self.params["stride_x"])
        self.params["size_y"] = 1 + (prev_layer_params["size_y"] + self.params["pad_y"] * 2 - self.params[
            "kernel_size"]) / (self.params["stride_y"])
        self.params["input_channels"] = prev_layer_params["output_channels"]

    def get_output_dimensions(self):
        return [self.params["size_x"], self.params["size_y"], self.params["output_channels"]]

    def get_input_dimensions(self):
        prev_layer_params = self.prev_layer.params
        return [prev_layer_params["size_x"], prev_layer_params["size_y"], prev_layer_params["output_channels"]]

    def get_weights_dimensions(self):
        return [self.params["kernel_size"], self.params["kernel_size"], self.params["output_channels"],
                self.params["input_channels"]]

    def get_cycles(self, hardware):

        if self.input_partition == None:
            # Get Weights from Memory
            latency_weights_request = 40

            latency_weights_fetch_first_conv = int(ceil(
                float(self.params["kernel_size"]) * self.params["kernel_size"] * hardware["data"][
                    "bytes_per_weight"] / (
                    hardware["resources"]["bandwidth"] / 4)))

            weight_fetch_cycles = int(ceil(float(self.params["kernel_size"] * self.params["kernel_size"] * \
                                                 self.params["input_channels"] * self.params["output_channels"] *
                                                 hardware["data"]["bytes_per_weight"]) / \
                                           min(hardware["resources"]["bandwidth"], hardware["config"][0])))

            compute_cycles = self.get_compute_cycles(hardware)
            if weight_fetch_cycles > compute_cycles:
                print "CRITCAL WARNING : Weight cycles {0} > Compute cycles {1} for convolution {2}".format(
                    weight_fetch_cycles, compute_cycles, self.params["name"])
            return max(weight_fetch_cycles, compute_cycles) + latency_weights_request + latency_weights_fetch_first_conv


        else:

            output_dimensions = self.get_output_dimensions()
            config = hardware["config"]
            print "Current Configuration = {0}".format(config)

            d = config[2]
            c = 1
            r = 1
            print "Config = {0}".format(config)
            print "Compute {0} x {1} x {2} at a time".format(r * config[0], c * config[1], d)

            num_iterations = int(ceil(float(output_dimensions[0]) / (config[0] * r))) * \
                             int(ceil(float(output_dimensions[1]) / (config[1] * c))) * \
                             int(ceil(float(output_dimensions[2]) / (d))) * \
                             self.params["input_channels"]

            print "Num of iterations = {0}".format(num_iterations)

            # compute_cycles = num_iterations * self.params["kernel_size"] * self.params["kernel_size"]
            compute_cycles = self.get_compute_cycles(hardware)

            # bw = min(hardware["resources"]["bandwidth"], config[0])
            bw = hardware["resources"]["bandwidth"]

            weights_fetch_latency = int(
                ceil(float(config[2] * self.params["kernel_size"] * self.params["kernel_size"]) / bw))

            ow = self.params["size_x"]
            iw = (ow - 1) * self.params["stride_x"] + self.params["kernel_size"]
            iw = int(ceil(float(iw) / config[0]) * config[0])
            initial_input_fetch_latency = int(ceil(float(iw * self.params["kernel_size"]) / bw))

            memory_access_cycles = self.get_memory_access_cycles(hardware)
            cycles = max(compute_cycles, memory_access_cycles) + weights_fetch_latency + initial_input_fetch_latency

            print "Cycles in conv = {0}".format(cycles)
            print "Compute Cycles in conv = {0:,}".format(compute_cycles)
            print "Memory access Cycles in conv = {0:,}".format(memory_access_cycles)

            print "Weight fetch cycles = {0:,}".format(weights_fetch_latency)

            return cycles

    def get_memory_access_cycles(self, hardware):

        if self.input_partition == None:
            # print "Error - no input partition"
            # exit(-1)
            latency_weights_request = 40
            latency_weights_fetch_first_conv = int(ceil(
                float(self.params["kernel_size"]) * self.params["kernel_size"] * hardware["data"][
                    "bytes_per_weight"] / (
                    hardware["resources"]["bandwidth"] / 4)))
            weight_fetch_cycles = int(ceil(float(self.params["kernel_size"] * self.params["kernel_size"] * \
                                                 self.params["input_channels"] * self.params["output_channels"] *
                                                 hardware["data"]["bytes_per_weight"]) / hardware["resources"][
                                               "bandwidth"]))
            return weight_fetch_cycles + latency_weights_fetch_first_conv + latency_weights_request

        else:
            print "Memory Accesses for Convolution = {0}".format(self.memory_accesses)
            latency_weights_request = 40
            return int(ceil(float(self.memory_accesses) / hardware["resources"]["bandwidth"])) + latency_weights_request

    def set_data_partition(self, in_dim, out_dim):
        self.input_partition = in_dim
        self.output_parition = out_dim

    def set_memory_accesses(self, accesses):
        self.memory_accesses = accesses

    def get_ideal_cycles(self, hardware):
        ops = self.get_ops(hardware)
        num_pes = min(hardware["resources"]["num_bram"], hardware["resources"]["num_macs"])
        return int(ceil(float(ops) / num_pes))

    def get_compute_cycles_batch(self, hardware, batch_size):
        print "*" * 50
        print "Input  block size = {0}".format(self.input_partition)
        print "Output block size = {0}".format(self.output_parition)
        print "Weight dimenstions = {0}".format(self.get_weights_dimensions())
        input_dimensions = self.prev_layer.get_output_dimensions()
        output_dimensions = self.get_output_dimensions()
        print "Input  Dimensions = {0}".format(input_dimensions)
        print "Output Dimensions = {0}".format(output_dimensions)
        print
        print "Batch Size = {0}".format(batch_size)
        print "*" * 50

        config = hardware["config"]
        print "Current Configuration = {0}".format(config)
        d = config[2]
        c = 1
        r = int(ceil(float(self.output_parition[0]) / config[0]))
        # if r > d:
        #     # print "Convolution Error : Need more compute blocks. Current config - {0}".format(config)
        #     r = d
        #     d = 1
        # else:
        #     d /= r
        print "Config = {0}".format(config)
        print "Compute {0} x {1} x {2} at a time".format(r * config[0], c * config[1], d)

        num_iterations = int(ceil(float(output_dimensions[0]) / (config[0] * r)) * r) * \
                         int(ceil(float(output_dimensions[1]) / (config[1] * c))) * \
                         int(ceil(float(output_dimensions[2] * batch_size) / (d))) * \
                         self.params["input_channels"]

        print "Num of iterations = {0}".format(num_iterations)

        compute_cycles = num_iterations * self.params["kernel_size"] * self.params["kernel_size"]

        print "Kernel size = {0}".format(self.params["kernel_size"])

        print "COMPUTE CYCLES = {0}".format(compute_cycles)
        print "COMPUTE CYCLES = {0}".format(
            num_iterations * self.params["kernel_size"] * self.params["kernel_size"])
        print "num_iterations = {0}".format(num_iterations)

        return compute_cycles


class Pooling(LayerNode):
    def __init__(self, layer_params):
        super(self.__class__, self).__init__(layer_params)
        if "pad_x" not in self.params:
            self.params["pad_x"] = 0
        if "pad_y" not in self.params:
            self.params["pad_y"] = 0
        if 'stride_x' not in self.params:
            self.params["stride_x"] = self.params["pool_x"]
        if "stride_y" not in self.params:
            self.params["stride_y"] = self.params["pool_y"]
        if "pool_x" not in self.params:
            self.params["pool_x"] = self.params["kernel_size"]
            self.params["pool_y"] = self.params["kernel_size"]

    def get_ops(self, hardware):
        # od = self.get_output_dimensions()
        # return od[0] * od[1] * od[2] * (self.params["pool_x"] * self.params["pool_y"])
        return 0

    def set_output_dimensions(self):
        # print "Pad_x = {0}, Pad_y = {1}".format(self.params["pad_x"], self.params["pad_y"])
        prev_layer_params = self.prev_layer.params
        self.params["size_x"] = 1 + int(
            ceil(float(prev_layer_params["size_x"] + self.params["pad_x"] * 2 - self.params["pool_x"]) / (
                self.params["stride_x"])))
        self.params["size_y"] = 1 + int(
            ceil(float(prev_layer_params["size_y"] + self.params["pad_y"] * 2 - self.params["pool_y"]) / (
                self.params["stride_y"])))
        self.params["input_channels"] = prev_layer_params["output_channels"]
        self.params["output_channels"] = prev_layer_params["output_channels"]

    def get_output_dimensions(self):
        return [self.params["size_x"], self.params["size_y"], self.params["input_channels"]]

    def get_compute_cycles(self, hardware):
        # # TODO : Change Pool Cycles
        # config = hardware["config"]
        # print "Pooling config = {0}".format(config)
        # output_dimensions = self.prev_layer.get_output_dimensions()
        # print "Pooling input dimensions = {0}".format(output_dimensions)
        # r = int(ceil(float(output_dimensions[0] / config[0])))
        # if r > config[2]:
        #     print "Pooling Error : Need more compute blocks. Current config - {0}".format(config)
        #     # sys.exit(-1)
        # c = int(floor(float(config[2]) / r))
        # if c * config[1] > output_dimensions[1]:
        #     c = 1
        # d = int(floor(float(config[2]) / (r * c)))
        # # print "M = {0}".format(c)
        # # print "Compute {0} x {1} x {2} at a time".format(r * config[0], c * config[1], d)
        #
        # num_iterations = int(ceil(float(output_dimensions[0]) / (config[0] * r))) * \
        #                  int(ceil(float(output_dimensions[1]) / (config[1] * c))) * \
        #                  int(ceil(float(output_dimensions[2]) / (d)))
        #
        # # print "Num of interations = {0}".format(num_iterations)
        #
        # compute_cycles = num_iterations * (2 * self.params["kernel_size"])

        compute_cycles = 0

        return compute_cycles
        # return self.get_output_elements() * self.params["pool_x"] * self.params["pool_y"]

    def get_block_input_dimensions(self, block):
        input_block = [(block[0] - 1) * self.params["stride_x"] + self.params["kernel_size"],
                       (block[1] - 1) * self.params["stride_y"] + self.params["kernel_size"], block[2]]
        self.params["reduced_output_dimensions"] = input_block
        input_dim = self.prev_layer.get_output_dimensions()
        for dim in xrange(2):
            if input_block[dim] > input_dim[dim] >= input_block[dim] - 2 * self.params["pad_x"] - 1:
                # print "patch size {0} < input dimensions {1}".format(input_block[dim], input_dim[dim])
                input_block[dim] = input_dim[dim]
            elif input_dim[dim] < input_block[dim]:
                print "Error patch size {0} < input dimensions {1}".format(input_block[dim], input_dim[dim])
        print block, self.params["name"], input_block
        return input_block

    def get_block_input_size(self, hardware, block):
        dim = self.get_block_input_dimensions(block)
        return dim[0] * dim[1] * dim[2] * hardware["data"]["bytes_per_element"]

        #######################


class Activation(LayerNode):
    def __init__(self, layer_params):
        super(self.__class__, self).__init__(layer_params)

    def get_compute_cycles(self, hardware):
        return self.get_output_elements()

    def set_output_dimensions(self):
        prev_layer_params = self.prev_layer.params
        self.params["size_x"] = prev_layer_params["size_x"]
        self.params["size_y"] = prev_layer_params["size_y"]
        self.params["output_channels"] = prev_layer_params["output_channels"]
        self.params["input_channels"] = prev_layer_params["output_channels"]

    def get_output_dimensions(self):
        return [self.params["size_x"], self.params["size_y"], self.params["output_channels"]]

    def get_ops(self, hardware):
        # od = self.get_output_dimensions()
        # return od[0] * od[1] * od[2]
        return 0

    def get_compute_cycles(self, hardware):
        return 0

    def get_memory_access_cycles(self, hardware):
        return 0

    #######################
    ## BLOCK FUNCTIONS

    def get_block_input_dimensions(self, patch):
        input_patch = patch
        print patch, self.params["name"], input_patch
        return input_patch

    def get_block_input_size(self, hardware, block):
        return 0

        #######################


class InnerProduct(LayerNode):
    def __init__(self, layer_params):
        super(self.__class__, self).__init__(layer_params)
        self.ip_batch = 1

    def set_output_dimensions(self):
        self.params["size_x"] = 1
        self.params["size_y"] = 1
        self.params["input_channels"] = self.params["output_channels"]

    def get_output_dimensions(self):
        return [self.params["size_x"], self.params["size_y"], self.params["output_channels"]]

    def get_weights_dimensions(self):
        return [self.prev_layer.get_output_elements(), self.params["output_channels"], 1, 1]

    def get_compute_cycles(self, hardware):
        return int(ceil(float(self.get_output_elements()) / hardware["resources"][
            "pes_per_pu"])) * self.prev_layer.get_output_elements()

    def get_ops(self, hardware):
        return self.get_output_elements() * self.prev_layer.get_output_elements()

    def get_input_block(self, batch):
        input_block = self.prev_layer.get_output_dimensions()
        return input_block

    def get_cycles(self, hardware):
        compute_cycles = self.get_compute_cycles(hardware)
        weight_cycles = self.get_memory_access_cycles(hardware)
        latency_weights_request = 40
        # if compute_cycles < data_cycles:
        #     print "inner product performance is bandwidth bound\n    Compute cycles = {0}\n    Data cycles = {1}".format(
        #         compute_cycles, data_cycles)
        if hardware["config"][2] == 1:
            return max(compute_cycles, weight_cycles) + latency_weights_request
        else:
            pes_per_pu = hardware["config"][0]
            num_pu = hardware["config"][2]
            bram_per_PE = int(ceil(float(hardware["resources"]["num_bram"]) / pes_per_pu))
            total_bram_capacity = pes_per_pu * hardware["resources"]["memory_per_bram"] / 8 * bram_per_PE * 0.8

            # self.prev_layer.print_layer(hardware)

            input_size = self.prev_layer.get_output_size(hardware)

            bw = min(hardware["resources"]["bandwidth"], pes_per_pu)

            ip_batches = int(ceil(float(input_size) / total_bram_capacity))
            # batch_size = min(total_bram_capacity, input_size)
            batch_size = 1

            input_latency = int(ceil((float(num_pu) * batch_size) / bw)) * ip_batches
            output_latency = (ip_batches - 1) * num_pu * self.get_output_size(hardware)

            total_cycles = max(compute_cycles, weight_cycles) + input_latency + output_latency + latency_weights_request

            print "input size = {0}".format(input_size)
            print "Inner-product num_batches = {0}".format(ip_batches)
            print "Inner-product Batch size  = {0}".format(batch_size)
            print "Time for input = {0}\nTime for weights = {1}".format(input_latency, weight_cycles)
            print "Total cycles for inner product = {0}".format(total_cycles)
            print "Cycles per input = {0}".format(int(ceil(float(total_cycles))))
            print "Config = {0}".format(hardware["config"])
            #
            # exit(-1)

            # return int(ceil(float(total_cycles) / num_pu))
            return total_cycles

    def get_compute_cycles(self, hardware):
        config = hardware["config"]
        # return int(ceil(float(self.prev_layer.get_output_elements()) * self.params["output_channels"]) / (
        #     config[0] * config[1] * config[2]))
        ops = self.prev_layer.get_output_elements() * self.params["output_channels"]
        # print "Total operations = {0}".format(ops)
        pes_per_pu = config[0]
        num_batches = config[2]
        # print "PEs per PU = {0}".format(pes_per_pu)
        compute_cycles = int(ceil(float(ops) / pes_per_pu))
        compute_cycles = int(ceil(float(compute_cycles) / num_batches))
        # print "Compute Cycles = {0}".format(compute_cycles)
        return compute_cycles

    def get_memory_access_cycles(self, hardware):
        # print "Inner Product Data cycles"
        latency_weights_request = 40
        w_dim = self.get_weights_dimensions()
        num_weights = w_dim[0] * w_dim[1] * w_dim[2] * w_dim[3]
        # print "Weight dimensions = {0}".format(w_dim)
        data_cycles = int(
            ceil(float(num_weights * hardware["data"]["bytes_per_element"]) / hardware["resources"][
                "bandwidth"])) + latency_weights_request

        config = hardware["config"]
        num_batches = config[2]

        data_cycles = int(ceil(float(data_cycles) / num_batches))

        # print "Inner Product Weights = {0}".format(num_weights)
        # print "Inner Product Weights Cycles = {0}".format(data_cycles)
        return data_cycles

    def get_ideal_cycles(self, hardware):
        ops = self.get_ops(hardware)
        # pes_per_pu = hardware["config"][0]
        num_pes = min(hardware["resources"]["num_bram"], hardware["resources"]["num_macs"])
        return int(ceil(float(ops) / num_pes))

    ############

    def get_cycles_batch(self, hardware, batch_size):
        if batch_size == 0:
            return self.get_cycles(hardware)
        compute_cycles = self.get_compute_cycles_batch(hardware, batch_size)
        weight_cycles = self.get_memory_access_cycles_batch(hardware, batch_size)
        latency_weights_request = 40

        pes_per_pu = int(ceil(hardware["config"][0] * hardware["config"][2] / batch_size))
        num_pu = batch_size
        print "config = {0} x {1}".format(pes_per_pu, num_pu)

        bram_per_PE = int(ceil(float(hardware["resources"]["num_bram"]) / pes_per_pu))
        total_bram_capacity = hardware["resources"]["memory_per_bram"] * pes_per_pu * bram_per_PE * num_pu / 8

        print "Total BRAM on chip = {0}MB".format(total_bram_capacity / 1024 / 1024)

        input_size = self.prev_layer.get_output_size(hardware)

        bw = hardware["resources"]["bandwidth"]

        input_batches = int(ceil(float(input_size) / total_bram_capacity))

        # input_latency = int(ceil((float(input_size) * batch_size) / bw)) * input_batches
        input_latency = 0
        output_latency = (input_batches - 1) * self.get_output_size(hardware)

        total_cycles = max(compute_cycles, weight_cycles) + input_latency + output_latency + latency_weights_request

        print "input size = {0}".format(input_size)
        # print "Inner-product num_batches = {0}".format(input_batches)
        print "Inner-product Batch size  = {0}".format(batch_size)
        print "Time for input = {0}\nTime for weights = {1}".format(input_latency, weight_cycles)
        print "Compute cycles = {0}".format(compute_cycles)
        print "Total cycles for inner product = {0}".format(total_cycles)
        print "Cycles per input = {0}".format(int(ceil(float(total_cycles))))
        print "Config = {0}".format(hardware["config"])
        #
        # exit(-1)

        # return int(ceil(float(total_cycles) / num_pu))
        return total_cycles

    def get_compute_cycles_batch(self, hardware, batch_size):
        if batch_size == 0:
            return self.get_compute_cycles(hardware)
        config = hardware["config"]
        # return int(ceil(float(self.prev_layer.get_output_elements()) * self.params["output_channels"]) / (
        #     config[0] * config[1] * config[2]))
        ops = self.prev_layer.get_output_elements() * self.params["output_channels"] * batch_size

        pes_per_pu = int(config[0] * config[2] / batch_size)
        num_pu = batch_size
        # print "PEs per PU = {0}".format(pes_per_pu)
        compute_cycles = int(ceil(float(ops) / pes_per_pu))
        compute_cycles = int(ceil(float(compute_cycles) / batch_size))
        print "Compute Cycles = {0}".format(compute_cycles)
        return compute_cycles

    def get_memory_access_cycles_batch(self, hardware, batch_size):
        if batch_size == 0:
            return self.get_memory_access_cycles(hardware)
        # print "Inner Product Data cycles"
        latency_weights_request = 40
        w_dim = self.get_weights_dimensions()
        num_weights = w_dim[0] * w_dim[1] * w_dim[2] * w_dim[3]
        print "Weight dimensions = {0}".format(w_dim)
        weight_size = num_weights * hardware["data"]["bytes_per_weight"]
        print "Weight size = {0}".format(weight_size)
        data_cycles = int(ceil(float(weight_size) /hardware["resources"]["bandwidth"])) + latency_weights_request

        pes_per_pu = int(ceil(hardware["config"][0] * hardware["config"][2] / batch_size))
        num_pu = batch_size
        # print "config = {0} x {1}".format(pes_per_pu, num_pu)

        bram_per_PE = int(ceil(float(hardware["resources"]["num_bram"]) / pes_per_pu))
        total_bram_capacity = hardware["resources"]["memory_per_bram"] * pes_per_pu * bram_per_PE * batch_size / 8

        print "Memory per BRAM = {0}".format(hardware["resources"]["memory_per_bram"])
        print "Total BRAM size = {0} MB".format(total_bram_capacity/1024/1024)
        print "Total weights = {0} MB".format(weight_size/1024/1024)

        # if weight_size < total_bram_capacity*0.7:
        #     data_cycles = 0
        #     print "Weights fit in memory"
        #     exit(-1)

        # print "Inner Product Weights = {0}".format(num_weights)
        # print "Inner Product Weights Cycles = {0}".format(data_cycles)
        return data_cycles


class Normalization(LayerNode):
    def __init__(self, layer_params):
        super(self.__class__, self).__init__(layer_params)
        if 'pad_x' not in self.params:
            self.params["pad_x"] = self.params["kernel_size"]
        if 'pad_y' not in self.params:
            self.params["pad_y"] = self.params["kernel_size"]
        if 'stride_x' not in self.params:
            self.params["stride_x"] = 1
        if 'stride_y' not in self.params:
            self.params["stride_y"] = 1

        if self.params["norm_region"] == 0:
            self.norm_type = "across_channel"
        else:
            self.norm_type = "within_channel"

        self.memory_accesses = None

    def get_cycles(self, hardware):

        config = hardware["config"]

        if config[3] > 1:
            compute_cycles = self.get_compute_cycles(hardware)
            return compute_cycles


        else:
            output_dimensions = self.get_output_dimensions()
            config = hardware["config"]

            d = config[2]
            print "Config = {0}".format(config)
            print "Compute {0} x {1} x {2} at a time".format(config[0], config[1], d)

            num_iterations = int(ceil(float(output_dimensions[0]) / (config[0]))) * \
                             int(ceil(float(output_dimensions[1]) / (config[1]))) * \
                             int(ceil(float(output_dimensions[2]) / (d))) * \
                             self.params["input_channels"]

            print "Num of iterations = {0}".format(num_iterations)

            compute_cycles = self.get_compute_cycles(hardware)

            bw = min(hardware["resources"]["bandwidth"], config[0])

            ow = self.params["size_x"]
            iw = (ow - 1) * self.params["stride_x"] + self.params["kernel_size"]
            iw = int(ceil(float(iw) / config[0]) * config[0])
            initial_input_fetch_latency = int(ceil(float(iw) / bw))

            memory_access_cycles = self.get_memory_access_cycles(hardware)
            cycles = max(compute_cycles, memory_access_cycles) + initial_input_fetch_latency

            print "Cycles in norm = {0}".format(cycles)
            print "Compute Cycles in norm = {0:,}".format(compute_cycles)
            print "Memory access Cycles in norm = {0:,}".format(memory_access_cycles)

            return cycles

    def get_compute_cycles(self, hardware):
        output_dimensions = self.get_output_dimensions()
        config = hardware["config"]
        d = config[2]
        r = int(ceil(float(output_dimensions[0]) / config[0]))
        # print "Config = {0}".format(config)
        # print "Output Dimensions = {0}".format(output_dimensions)
        # print "Number of blocks per row = {0}".format(r)
        if r > config[2]:
            # print "Convolution Error : Need more compute blocks. Current config - {0}".format(config)
            r = config[2]
        d /= r
        c = 1
        print "Compute {0} x {1} x {2} at a time".format(r * config[0], c * config[1], d)

        num_iterations = int(ceil(float(output_dimensions[0]) / (config[0] * r))) * \
                         int(ceil(float(output_dimensions[1]) / (config[1] * c))) * \
                         int(ceil(float(output_dimensions[2]) / (d)))

        # print "Num of interations = {0}".format(num_iterations)

        if self.norm_type == "within_channel":
            compute_cycles = num_iterations * (self.params["kernel_size"] * self.params["kernel_size"])
        else:
            compute_cycles = num_iterations * (self.params["kernel_size"])

        # compute_cycles = 0

        return compute_cycles

    def set_output_dimensions(self):
        prev_layer_params = self.prev_layer.params
        self.params["size_x"] = prev_layer_params["size_x"]
        self.params["size_y"] = prev_layer_params["size_y"]
        self.params["input_channels"] = prev_layer_params["input_channels"]
        self.params["output_channels"] = self.params["input_channels"]

    def get_output_dimensions(self):
        return [self.params["size_x"], self.params["size_y"], self.params["output_channels"]]

    def get_ops(self, hardware):
        od = self.get_output_dimensions()
        if self.norm_type == "within_channel":
            return od[0] * od[1] * od[2] * (self.params["kernel_size"] * self.params["kernel_size"])
        else:
            return od[0] * od[1] * od[2] * self.params["kernel_size"]

    def get_memory_access_cycles(self, hardware):

        config = hardware["config"]
        # bw = min(config[0]*(int(hardware["resources"]["bandwidth"]/config[0])), hardware["resources"]["bandwidth"])
        # if bw == 0:
        #     bw = hardware["resources"]["bandwidth"]
        bw = hardware["resources"]["bandwidth"]

        if self.norm_type == "within_channel":
            # print "WITHIN CHANNEL"
            # exit(-1)
            latency_input_request = 40
            latency_inputs_fetch_first_row = int(ceil(
                float(self.params["kernel_size"]) * self.params["size_x"] * config[2] * hardware["data"][
                    "bytes_per_weight"] / (
                    float(hardware["resources"]["bandwidth"]) / 4)))

            if self.memory_accesses == None:
                input_fetch_cycles = int(ceil(float(self.params["size_x"] * self.params["size_y"] * \
                                                    self.params["input_channels"] * \
                                                    hardware["data"]["bytes_per_element"]) / bw))
            else:
                input_fetch_cycles = int(ceil(float(self.memory_accesses) / bw))
            return input_fetch_cycles + latency_inputs_fetch_first_row + latency_input_request

        else:
            latency_input_request = 40
            od = self.get_output_dimensions()
            # print "Output Dimensions = {0}".format(od)

            if self.memory_accesses == None:
                mem_size = int(
                    ceil(float(od[0]) / config[0]) * config[0] * od[1] * od[2] * hardware["data"]["bytes_per_element"])
                # print "Mem Size = {0}".format(mem_size)

                latency_input_fetch = int(ceil(float(mem_size) / bw))
            else:
                latency_input_fetch = int(ceil(float(self.memory_accesses) / bw))

            # print "Bandwidth = {0}".format(bw)
            # print "Cycles = {0}".format(latency_input_fetch)

            return latency_input_request + latency_input_fetch

    def get_ideal_cycles(self, hardware):
        ops = self.get_ops(hardware)
        num_pes = min(hardware["resources"]["num_bram"], hardware["resources"]["num_macs"])
        return int(ceil(float(ops) / num_pes))

    def print_layer(self, hardware):
        print 'Layer {0}:'.format(self.params["type"])
        print '  --Dimensions of Output Data:\t\t{0}'.format(self.get_output_dimensions())

        od = self.get_output_dimensions()
        out_size = od[0] * od[1] * od[2] * hardware["data"]["bytes_per_element"]
        print '  --Size of Output in Bytes:\t\t{0:,} Bytes'.format(out_size)

        print "  --Number of Operations:\t\t{0:,}".format(self.get_ops(hardware))
        print '  --Size of Output Data:\t\t{0:,} elements'.format(self.get_output_elements())
        print '  --Dimensions of Weights:\t\t{0}'.format(self.get_weights_dimensions())
        print '  --Size of Weights:\t\t\t{0} Bytes'.format(self.get_weights_size(hardware))
        print '  --Type of LRN:\t\t\t{0}'.format(self.norm_type)
        print '  --Kernel Size:\t\t\t{0}'.format(self.params["kernel_size"])
        # print "  --Output buffer depth used:\t\t{0:,}".format(self.get_output_buffer_depth(hardware))
        # print '  --Output buffer size used:\t\t{0} KB'.format(self.get_output_buffer_size(hardware))
        self.print_cycles(hardware)
        print

    def set_memory_accesses(self, accesses):
        self.memory_accesses = accesses


class DataOut(LayerNode):
    def __init__(self, layer_params):
        super(self.__class__, self).__init__(layer_params)

    def set_output_dimensions(self):
        size_prev = self.prev_layer.get_output_dimensions()
        self.params["size_x"] = size_prev[0]
        self.params["size_y"] = size_prev[1]
        self.params["input_channels"] = size_prev[2]

    def get_output_dimensions(self):
        return self.prev_layer.get_output_dimensions()

    def get_compute_cycles(self, hardware):
        return 0

    def get_memory_access_cycles(self, hardware):
        # TODO: Can make this lower
        return int(ceil(
            float(self.get_output_elements() * hardware["data"]["bytes_per_element"]) / hardware["resources"][
                "bandwidth"])) + \
               20
