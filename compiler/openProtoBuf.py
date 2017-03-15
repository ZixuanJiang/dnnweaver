import caffe_pb2
from google.protobuf.text_format import Merge
import sys

def readProtoBuf(f):
    net = caffe_pb2.NetParameter()
    Merge((open(f,'r').read()), net)

    # NAME
    out = {}
    out["name"] = net.name
    out["layers"] = []

    #INPUT
    data_Layer = {}
    data_Layer["name"] = "data"
    data_Layer["type"] = "DATA"
    try:
        input_dim = net.input_shape[0].dim
    except IndexError:
        input_dim = net.input_dim

    data_Layer["size_x"] = int(input_dim[3])
    data_Layer["size_y"] = int(input_dim[2])
    data_Layer["output_channels"] = int(input_dim[1])
        # print net.input_dim
        # sys.exit(0)
    # data_Layer["output"] = "data"
    out["layers"].append(data_Layer)

    print net.name
    # print "Layers:"
    layer_count = 0
    compute_layers = []
    layer_types = ["convolution", "innerproduct", "relu", "pooling", "lrn"]
    prev_output = ["data_in"]

    if (len(net.layer) == 0):
        list_of_layers = net.layers
        # print list_of_layers
        # print list_of_layers[0]
        # sys.exit(0)
    else:
        list_of_layers = net.layer
    for l in list_of_layers:
        # print l.name, str(l.type)
        if (str(l.type).lower() == "convolution"):
            # print "Type: Convolution"
            # print l.name
            # {
            #   "input": "data",
            #   "output": "relu1",
            #   "name": "conv1",
            #   "type": "CONVOLUTION",
            #   "kernel_count": 96,
            #   "kernel_size": 7,
            #   "stride": 2
            # },
            tmp = {}
            tmp["type"] = "CONVOLUTION"
            tmp["input"] = out["layers"][-1]["name"]
            tmp["name"] = l.name
            tmp["group"] = l.convolution_param.group
            tmp["output_channels"] = l.convolution_param.num_output
            tmp["kernel_size"] = l.convolution_param.kernel_size
            tmp["pad"] = l.convolution_param.pad
            tmp["stride"] = l.convolution_param.stride
            out["layers"][-1]["output"] = tmp["name"]
            out["layers"].append(tmp)


        elif (str(l.type).lower() == "innerproduct"):
            # print "Type: Inner Product"
            # print l.name
            # {
            #   "input": "relu6",
            #   "output": "relu7",
            #   "name": "fc7",
            #   "type": "INNERPRODUCT",
            #   "neurons": 4096
            # },
            tmp = {}
            tmp["input"] = out["layers"][-1]["name"]
            tmp["name"] = l.name
            tmp["type"] = "INNERPRODUCT"
            tmp["output_channels"] = l.inner_product_param.num_output
            out["layers"][-1]["output"] = tmp["name"]
            out["layers"].append(tmp)


        elif (str(l.type).lower() == "relu"):
            # print "Type: ReLU"
            # print l.name
            # {
            #   "input": "conv1",
            #   "output": "norm1",
            #   "name": "relu1",
            #   "type": "RELU"
            # },
            tmp = {}
            tmp["input"] = out["layers"][-1]["name"]
            tmp["name"] = l.name
            tmp["type"] = "RELU"
            out["layers"][-1]["output"] = tmp["name"]
            out["layers"].append(tmp)



        elif (str(l.type).lower() == "pooling"):
            # print "Type: Pooling"
            # print l.name
            # {
            #   "input": "norm1",
            #   "output": "conv2",
            #   "name": "pool1",
            #   "type": "POOLING",
            #   "kernel_size": 3,
            #   "stride": 3
            # },
            tmp = {}
            tmp["input"] = out["layers"][-1]["name"]
            tmp["name"] = l.name
            tmp["type"] = "POOLING"
            tmp["pad"] = l.convolution_param.pad
            tmp["kernel_size"] = l.pooling_param.kernel_size
            tmp["stride"] = l.pooling_param.stride
            out["layers"][-1]["output"] = tmp["name"]
            out["layers"].append(tmp)


        elif (str(l.type).lower() == "lrn"):
            # print "Type: Normalization"
            # print l.name
            # {
            #     "name": "norm1",
            #     "type": "LRN",
            #     "input": "pool1",
            #     "output": "conv2",
            #     "local_size": 5
            # },
            tmp = {}
            tmp["input"] = out["layers"][-1]["name"]
            tmp["name"] = l.name
            tmp["type"] = "LRN"
            tmp["norm_region"] = l.lrn_param.norm_region
            tmp["kernel_size"] = l.lrn_param.local_size
            out["layers"][-1]["output"] = tmp["name"]
            out["layers"].append(tmp)

        # else:
        #     print "ignoring layer: {0}".format(str(l.type))

        if str(l.type).lower() in layer_types:
            layer_count+=1
            if prev_output != l.bottom and not len(out["layers"]) == 2:
                # print str(prev_output[0]), out["layers"][-1]["input"], l.top
                raise Exception("Previous layer's top is not the same as this layer's bottom")
                sys.exit(0)


        prev_output = l.top





    print "Total parsed layers = {0}".format(layer_count)


    #OUTPUT
    output_Layer = {}
    output_Layer["name"] = "output"
    output_Layer["input"] = out["layers"][-1]["name"]
    out["layers"][-1]["output"] = output_Layer["name"]
    output_Layer["type"] = "OUTPUT"
    output_Layer["size_x"] = input_dim[0]
    output_Layer["size_y"] = input_dim[1]
    output_Layer["channels"] = input_dim[2]
    out["layers"].append(output_Layer)

    # print "\n\n\nPARSED {0} LAYERS:".format(len(out["layers"]))
    # for layer in out["layers"]:
        # print "NAME:{0}".format(layer["name"])
        # if ("input" in layer):
        #     print "INPUT:{0}".format(layer["input"])
        # if ("output" in layer):
        #     print "OUTPUT:{0}".format(layer["output"])
        # print

    # sys.exit(0)
    return out



