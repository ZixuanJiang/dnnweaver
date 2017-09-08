#include <stdio.h>
#include <assert.h>
#include <stdlib.h>
#include <unistd.h>

//c++
#include <string>
#include <iostream>
#include <fstream>

#include"accelerator.h"


#define WEIGHT_RD_ADDR  0x08000000
#define DATA_RD_ADDR    0x080005B0

using namespace std;

typedef short DType;


void initialize_mem_null (
    volatile DType* addr,
    int len) {
  int i;
  for (i=0; i<len; i++) {
    *(addr+i) = 0;
  }
  //cma_cache_clean((char*)addr, len);
}

void print_mem (
    volatile DType* addr,
    int len) {
  int i;
  //cma_cache_clean((char*)addr, len);
  for (i=0; i<len; i++) {
    printf ("%7d ", *(addr+i));
  }
  printf ("\n\r ");
}

void print_fm (
    volatile DType* addr,
    int width,
    int height) {

  int w, h;
  int offset = 0;
  //cma_cache_clean((char*)addr, width * height);
  printf ("\n");
  for (h=0; h<height; h++) {
    for (w=0; w<width; w++, offset++) {
      printf ("%8x: %8d | ", offset*sizeof(DType), *(addr+offset));
    }
    printf("\n");
  }
  printf ("\n\r ");
}


int main(int argc, char* argv[])
{

  //assert (argc > 3);
  //int iterations = atoi(argv[1]);
  //int num_weights = atoi(argv[2]);
  //int num_data = atoi(argv[3]);

  assert (argc > 3);
  string mem_file = string(argv[1]);
  string weight_file = string(argv[2]);
  string input_file = string(argv[3]);

  printf("DnnWeaver Loopback Test : \n\r ");
  int i;

  accelerator<DType> a(mem_file.c_str());

  a.print_registers();

  // a.initialize_weights_from_file("weights.bin");
  // a.initialize_read_data_from_file("input.bin");

  a.initialize_read_data();
  a.initialize_write_data_null();
  //a.convolution(0);
  //a.pooling(0);
  a.start();
  sleep(1);
  a.print_registers();
  a.print_write_data();
  //a.print_write_data(1);
  //a.print_write_data_vector(2);
  //a.print_write_data_vector(3);

  printf ("Done\n");

  return 0;
}
