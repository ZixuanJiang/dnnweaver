#!/usr/local/bin/python
from math import pow
from DWlayer import int_to_bin

total_bits = 16
frac_bits = 10
factor = 1 << frac_bits

def normalization (k_, alpha_, beta_, n_, sqsum):
    #print("Alpha = {0}, Beta = {1}".format(alpha_, beta_))
    tmp = k_ + alpha_*sqsum/n_
    #print("val = {0}".format(tmp))
    x = pow(tmp, -1*beta_)
    #print ("norm({0}) = {1}".format(i, x))
    return x

if __name__ == "__main__":
    alpha = 0.0001
    beta = 0.75
    n = 5
    K = 1
    filename = "norm_lut.csv"
    with open(filename, 'wb') as b:
        for i in range(0, 1 << 16, 1<<8):
            j = float(i)
            k = normalization(K, alpha, beta, n, j)
            l = int(k*factor)
            b.write("{0},{1},{2}\n".format(j, k, l))

    with open("../fpga/hardware/include/norm_lut.vh", 'wb') as lut:
        for i in range (0, 1<<11):
            lut.write(int_to_bin(i, 16))
            lut.write("\n")
