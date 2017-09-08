#include<iostream>

#define SHARED_MEM_SIZE 0x38000000
#define SHARED_START    0x08000000

#define CONTROL_ADDRESS 0x43c00000
#define CONTROL_SIZE    16

struct size_vec4{
  size_t d0;
  size_t d1;
  size_t d2;
  size_t d3;
};

template<typename T>
class accelerator {
  T* buffer; // Pointer to shared memory space
  volatile unsigned int* master_addr; // Pointer to the accelerator's register space
  size_t num_layers;
  T** rd_addr;
  T** wr_addr;
  T** weight_addr;
  int* l_type;
  size_vec4* rd_size;
  size_vec4* wr_size;
  size_vec4* weight_size;
  size_t num_pe;
  size_t num_pu;
  public:
  accelerator(const char* filename);
  ~accelerator();
  void start();
  void print_registers();
  void initialize_read_data();
  void initialize_write_data_null();
  void initialize_weights();
  void initialize_read_data(size_t);
  void initialize_read_data_from_file(const char* filename);
  void initialize_write_data_null(size_t);
  void initialize_weights_from_file(const char* filename);
  void initialize_weights(size_t);
  void initialize_weights_matrix(size_t);
  void print_write_data();
  void print_write_data(size_t);
  void print_write_data_vector(size_t);
  void get_network_config(const char*);
  void convolution(size_t);
  void pooling(size_t);
};
  
