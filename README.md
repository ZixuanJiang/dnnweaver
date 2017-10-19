#DnnWeaver
**DnnWeaver** is the first open-source framework for accelerating Deep Neural Networks (DNNs) on FPGAs.
While FPGAs are an attractive choice for accelerating DNNs, programming an FPGA is difficult.
With **DnnWeaver**, our aim is to bridge the semantic gap between the high-level specifications of DNN models used by programmers and FPGA acceleration.
With our framework, the programmer only specifies the Deep Neural Network using Caffe format.
The framework automatically generates an accelerator specialized for the given network.

**DnnWeaver** is under development at the Alternative Computing Technologies (ACT) Laboratory, Georgia Institute of Technology.

## Citing us
If you use this work, please cite our paper published in The 49th Annual IEEE/ACM International Symposium on Microarchitecture (MICRO), 2016.

```
H. Sharma, J. Park, D. Mahajan, E. Amaro, J. K. Kim, C. Shao, A. Mishra, H. Esmaeilzadeh, "From High-Level Deep Neural Models to FPGAs", in the Proceedings of the 49th Annual IEEE/ACM International Symposium on Microarchitecture (MICRO), 2016.
```

## Build Instructions

These are the dependencies for DnnWeaver:
```
1. iverilog (optional)
2. python 2.7
3. Xilinx Vivado 2016.2
```


In addition, PetaLinux Tools are required. Please [download PetaLinux](https://www.xilinx.com/support/download/index.html/content/xilinx/en/downloadNav/embedded-design-tools.html) and refer to the [PetaLinux Wiki](http://www.wiki.xilinx.com/PetaLinux) for more information.

In **dnnweaver.public/fpga/** directory, provide a customizable config file for Makefile by using the following command:

```
cp Makefile.config.example Makefile.config
```

Edit **Makefile.config** appropriately based on your Vivado version, path to Vivado and etc.

Define the prototxt file for the DNN model in Caffe format in the Makefile.

To generate the accelerator Verilog, use the following command in the fpga directory:
```
make PROTOTXT=your_prototxt_here
```
The make command would create an output folder **synthesis-output** with the bit-file for the FPGA:
```
synthesis-output/zynq_wrapper.bit #bit-file to program the FPGA
```

We provide a simple API to communicate with the accelerator, along with a sample code *linux.c* demonstrating how to use the API. The API can be found here:
```
fpga/arm_software/
```
By default, the make command will compile the sample *linux.c* and generate an executable in the following path:
```
fpga/synthesis_output/linux.elf
```

## Benchmark DNNs
We are actively improving DnnWeaver by adding more benchmark DNN models and supporting more types of layers.
We are also working towards architectural improvements which would lead to an increase in performance and dynamic utilization of the FPGA's resources.
The initial set of benchmarks are listed below.
```
1. LeNet: MNIST Dataset
2. Cifar-10 Full: Cifar-10 Dataset
3. NiN: ILSVRC2012 Dataset
4. Djinn-ASR: Djinn and Tonic
5. AlexNet: ILSVRC2012
6. VGG-CNN-S: ILSVRC2012
7. Overfeat: ILSVRC2012
8. VGG-16: ILSVRC2012
```
The above benchmarks can be found in compiler/sample\_prototxt/*

## License

```
Copyright 2017 Hadi Esmaeilzadeh

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

## Maintained By
Hardik Sharma (*hsharma@gatech.edu*)