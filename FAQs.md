# FAQs

## Problem
```Traceback (most recent call last): 
 File "../compiler/compiler.py", line 4, in <module> 
   import caffe_pb2 
 File "/home/$USER/dnnweaver/compiler/caffe_pb2.py", line 6, in <module> 
   from google.protobuf.internal import enum_type_wrapper 
ImportError: No module named google.protobuf.internal 
Makefile:157: recipe for target 'hardware/include/pu_controller_bin.vh' failed 
make: *** [hardware/include/pu_controller_bin.vh] Error 1
```

## Solution
`sudo apt-get install python-protobuf`

## Problem
Issues relate to Makefile or Makefile.config

## Solution
Read *Build Instructions* in the [README](https://bitbucket.org/hsharma35/dnnweaver.public/src)