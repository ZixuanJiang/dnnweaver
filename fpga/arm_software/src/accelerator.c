#include"accelerator.h"
#include<fstream>
#include"cma.h"
#include<sys/time.h>
#include<iomanip>

size_t ceil_a_by_b(size_t a, size_t b) {
  if (a < b) return 1;
  else {
    if (a%b == 0) return a/b;
    else return a/b+1;
  }
}

template <typename T>
accelerator<T>::accelerator(const char* filename) {

  std::cout << "Calling constructor" << std::endl;

  int dh = open("/dev/mem", O_RDWR | O_SYNC); // Open /dev/mem which represents the whole physical memory
  master_addr = (volatile unsigned int*) mmap(NULL, CONTROL_SIZE, PROT_READ | PROT_WRITE, MAP_SHARED, dh, CONTROL_ADDRESS); // Memory map AXI Lite register block
  if (master_addr == NULL) {
    printf ("Can't allocate master addr\n\r ");
  }

  buffer = (T*) mmap(NULL, SHARED_MEM_SIZE, PROT_READ | PROT_WRITE, MAP_SHARED, dh, SHARED_START);
  if (buffer == NULL) {
    printf ("Can't allocate buffer\n\r ");
  }

  std::cout << "Getting MMAP from: " << filename << std::endl;
  std::ifstream ifs(filename);
  if (!ifs) {
    std::cout << "Can't open file " << filename << std::endl;
  }
  ifs >> num_layers;
  std::cout << "Number of layers " << num_layers << std::endl;
  rd_addr = (T**) malloc (num_layers * sizeof (T*));
  wr_addr = (T**) malloc (num_layers * sizeof (T*));
  weight_addr = (T**) malloc (num_layers * sizeof (T*));

  rd_size = (size_vec4*) malloc (num_layers* sizeof(size_vec4));
  wr_size = (size_vec4*) malloc (num_layers* sizeof(size_vec4));
  weight_size = (size_vec4*) malloc (num_layers* sizeof(size_vec4));

  l_type = (int*) malloc (num_layers*sizeof(int));

  size_t d0, d1, d2, d3;

  ifs >> num_pe;
  ifs >> num_pu;

  std::cout << "Accelerator configuration " << num_pe << " x " << num_pu << std::endl;

  size_t tmp;

  for (int ii = 0; ii < num_layers; ii++) {

    ifs >> l_type[ii];

    ifs >> tmp >> d0 >> d1 >> d2 >> d3;
    std::cout << "Physical Layer read addr " << std::hex << tmp << std::dec << std::endl;
    new(&rd_addr[ii]) T*(buffer + (tmp - SHARED_START)/sizeof(T));
    std::cout << "Virtual Layer read addr " << std::hex << rd_addr[ii] << std::dec << std::endl;
    std::cout << "Size = " << d0 << " x " << d1 << " x " << d2 << " x " << d3 << std::endl;
    rd_size[ii] = {d0, d1, d2, d3};

    ifs >> tmp >> d0 >> d1 >> d2 >> d3;
    std::cout << "Physical Layer weights addr " << std::hex << tmp << std::dec << std::endl;
    new(&weight_addr[ii]) T*(buffer + (tmp - SHARED_START)/sizeof(T));
    std::cout << "Virtual Layer weights addr " << std::hex << weight_addr[ii] << std::dec << std::endl;
    std::cout << "Size = " << d0 << " x " << d1 << " x " << d2 << " x " << d3 << std::endl;
    weight_size[ii] = {d0, d1, d2, d3};

    ifs >> tmp >> d0 >> d1 >> d2 >> d3;
    std::cout << "Physical Layer write addr " << std::hex << tmp << std::dec << std::endl;
    new(&wr_addr[ii]) T*(buffer + (tmp - SHARED_START)/sizeof(T));
    std::cout << "Virtual Layer write addr " << std::hex << wr_addr[ii] << std::dec << std::endl;
    std::cout << "Size = " << d0 << " x " << d1 << " x " << d2 << " x " << d3 << std::endl;
    wr_size[ii] = {d0, d1, d2, d3};

  }
}

template <typename T>
accelerator<T>::~accelerator() {
  std::cout << "Calling destructor" << std::endl;
  munmap((void*)master_addr, CONTROL_SIZE);
  munmap(buffer, SHARED_MEM_SIZE);
  free(rd_addr);
  free(wr_addr);
  free(weight_addr);
  for (int ii=0; ii<num_layers; ii++) {
    //free(rd_size[ii]);
    //free(wr_size[ii]);
    //free(weight_size[ii]);
  }
  //free(rd_size);
  //free(wr_size);
  //free(weight_size);
}

template <typename T>
void accelerator<T>::print_registers() {
  std::cout << "Printing registers for the accelerator" << std::endl;

  std::cout << "rd cfg idx  = " << *(master_addr+8) << std::endl;
  std::cout << "wr cfg idx  = " << *(master_addr+9) << std::endl;

  std::cout << "PU0 write count  = " << *(master_addr+12) << std::endl;
  std::cout << "PU1 write count  = " << *(master_addr+13) << std::endl;

  std::cout << "Vectorgen Reads = " << *(master_addr+6) << std::endl;
  std::cout << "Vecgen state = " << *(master_addr+7) << std::endl;

  std::cout << "Start count =  " << *(master_addr+0) << std::endl;
  std::cout << "Done  count =  " << *(master_addr+1) << std::endl;
  std::cout << "read  count =  " << *(master_addr+10) << std::endl;
  std::cout << "write count =  " << *(master_addr+11) << std::endl;

  std::cout << "Buffer Reads =  " << *(master_addr+14) << std::endl;
  std::cout << "Stream Reads =  " << *(master_addr+15) << std::endl;

  std::cout << "PU state =  " << *(master_addr+2) << std::endl;

  //std::cout << "Write Address 0 = %x\n\r ", *(master_addr+2));
  //std::cout << "Write Address 1 = %x\n\r ", *(master_addr+3));
  //std::cout << "Write Address 2 = %x\n\r ", *(master_addr+4));
  //std::cout << "Write Address 3 = %x\n\r ", *(master_addr+5));
}

template <typename T>
void accelerator<T>::start()
{
  std::cout << "Starting Accelerator" << std::endl;
  *(this->master_addr + 0) = *(this->master_addr + 0) + 1;
}

template <typename T>
void accelerator<T>::initialize_read_data() {
  std::cout << "Initializing read data for Network " << std::endl;
  for (int l=0; l<num_layers; l++) {
    initialize_read_data(l);
  }
}

template <typename T>
void accelerator<T>::initialize_read_data(size_t idx) {
  std::cout << "Initializing read data for Layer " << idx << std::endl;
  T* addr = rd_addr[idx];
  size_t hmax = rd_size[idx].d3;
  size_t wmax = rd_size[idx].d2;
  size_t wmax_pad = rd_size[idx].d2;
  size_t cmax = rd_size[idx].d1;
  if (wmax_pad%num_pe != 0)
    wmax_pad += num_pe - wmax_pad%num_pe;
  size_t offset, value;
  size_t len = wmax_pad * hmax * cmax;
  for (int ic=0; ic<cmax; ic++) {
    for (size_t w_count=0; w_count<wmax_pad; w_count++) {
      for (size_t h_count=0; h_count<hmax; h_count++) {
        offset = w_count + wmax_pad*(h_count+hmax*ic);
        if (w_count < wmax) {
          value = w_count+wmax*(h_count);
        } else {
          value = 0;
        }
        *(addr+offset) = value;
      }
    }
  }
  cma_cache_clean((char*)addr, len);
}

template <typename T>
void accelerator<T>::initialize_write_data_null() {
  std::cout << "Initializing write data for Network" << std::endl;
  for (int l=0; l<num_layers; l++) {
    initialize_write_data_null(l);
  }
}

template <typename T>
void accelerator<T>::initialize_write_data_null(size_t idx) {
  std::cout << "Initializing write data for Layer " << idx << std::endl;
  size_t padded_w = wr_size[idx].d3 + wr_size[idx].d3%num_pe;
  size_t len = padded_w * wr_size[idx].d1 * wr_size[idx].d2;
  std::cout << "write data dimensions = " << len << std::endl;
  T* addr = wr_addr[idx];
  for (int i=0; i<len; i++) {
    *(addr+i) = 0;
  }
  cma_cache_clean((char*)addr, len);
}

template <typename T>
void accelerator<T>::initialize_weights() {
  std::cout << "Initializing weights for Network " << std::endl;
  for (int l=0; l<num_layers; l++) {
    if (l_type[l] == 0)
      initialize_weights(l);
    else
      initialize_weights_matrix(l);
  }
}

template <typename T>
void accelerator<T>::initialize_weights(size_t idx) {
  std::cout << "Initializing weights for Layer " << idx << std::endl;
  size_t padded_len = weight_size[idx].d2 * weight_size[idx].d3;
  padded_len = 4 + ceil_a_by_b(padded_len, 4) * 4;
  size_t len = weight_size[idx].d0 * weight_size[idx].d1 * padded_len;
  std::cout << "write data dimensions = " << len << std::endl;
  T* addr = weight_addr[idx];
  size_t num_weights = weight_size[idx].d0 * weight_size[idx].d1;
  for (int j=0; j<num_weights; j++) {
    //std::cout << std::hex << (addr+j*padded_len) << std::dec << std::endl;
    for (int i=0; i<padded_len; i++) {
      if (i < 4)
        *(addr+i+j*padded_len) = 0;
      else
        *(addr+i+j*padded_len) = i-4;
    }
  }
  cma_cache_clean((char*)addr, len);
}

template <typename T>
void accelerator<T>::initialize_weights_matrix(size_t idx) {
  std::cout << "Initializing weights for Layer " << idx << std::endl;
  size_t oc = weight_size[idx].d0;
  oc += (oc % num_pe == 0) ? 0 : num_pe - oc%num_pe;
  size_t ic = weight_size[idx].d2 + 1;
  size_t len = oc*ic;
  std::cout << "write data dimensions = " << len << std::endl;
  T* addr = weight_addr[idx];
  size_t offset = 0;
  for (size_t jj=0; jj<oc; jj++) {
    for (size_t ii=0; ii<ic; ii++, offset++) {
      *(addr+offset) = offset;
      //if (jj == 0)std::cout << std::setw(6) <<
      //std::dec << *(addr+offset) << " ";
      //if (jj == 0 && ii == ic-1)
      //std::cout << std::endl;
    }
  }
  cma_cache_clean((char*)addr, len);
}

template <typename T>
void accelerator<T>::print_write_data_vector(size_t idx) {
  T* addr = wr_addr[idx];
  size_t len = wr_size[idx].d1;
  cma_cache_clean((char*)addr, len);
  std::cout << "Printing output for Layer " << idx << std::endl;
  size_t offset = 0;
  for (size_t w=0; w<len; w++, offset++) {
    std::cout << std::setw(6) << std::dec << *(addr+offset) << " ";
    if (w%16 == 15)
      std::cout << std::endl;
  }
  std::cout << std::endl;
}

template <typename T>
void accelerator<T>::print_write_data() {
  std::cout << "Printing output for Network " << std::endl;
  for (size_t l=0; l<num_layers; l++) {
    print_write_data(l);
  }
}


template <typename T>
void accelerator<T>::print_write_data(size_t idx) {
  T* addr = wr_addr[idx];
  size_t padded_w = wr_size[idx].d3;
  if (padded_w % num_pe != 0)
    padded_w += num_pe - padded_w%num_pe;
  size_t fm_size = padded_w * wr_size[idx].d2;
  size_t len = fm_size * wr_size[idx].d1;
  cma_cache_clean((char*)addr, len);
  std::cout << "Printing output for Layer " << idx << std::endl;
  size_t offset = 0;
  for (size_t oc=0; oc<wr_size[idx].d1; oc++) {
    for (size_t h=0; h<wr_size[idx].d2; h++) {
      for (size_t w=0; w<padded_w; w++, offset++) {
        std::cout << std::setw(6) << std::dec << *(addr+offset) << " ";
      }
      std::cout << std::endl;
    }
    std::cout << std::endl;
  }
}

template <typename T>
void accelerator<T>::convolution(size_t idx) {
  T* out = wr_addr[idx];
  T* in = rd_addr[idx];
  T* weight = weight_addr[idx];
  std::cout << "Applying Convolution to Layer number " << idx << std::endl;
  size_t output_offset = 0;
  size_t input_offset = 0;
  size_t input_fm_w = rd_size[idx].d2;
  input_fm_w = ceil_a_by_b(input_fm_w, num_pe) * ceil_a_by_b(num_pe, 4)*4;
  size_t input_fm_h = rd_size[idx].d3;
  size_t input_fm_len = input_fm_w * input_fm_h;

  size_t weight_offset = 0;
  size_t weight_len = ceil_a_by_b(wr_size[idx].d2 * wr_size[idx].d3, 4);

  size_t conv_out_w = rd_size[idx].d2 - weight_size[idx].d2+1;
  size_t conv_out_h = rd_size[idx].d3 - weight_size[idx].d3+1;
  
  T in_data, wgt_data, out_data, bias;

  //for (size_t oc=0; oc<wr_size[idx].d1;oc++) {
  for (size_t oc=0; oc<1;oc++) {
    std::cout << "Output Channel " << oc << std::endl;
    for (size_t ic=0; ic<rd_size[idx].d1; ic++) {
      bias = *(weight);
      weight += 4;
      std::cout << "Bias = " << bias << std::endl;
      for (size_t oh=0; oh<conv_out_h; oh++) {
        for (size_t ow=0; ow<conv_out_w; ow++) {
      //for (size_t oh=0; oh<1; oh++) {
        //for (size_t ow=0; ow<1; ow++) {
          output_offset = ow + conv_out_w * (oh + conv_out_h * ic);
          if (ic == 0)
            *(out+output_offset) = bias;
          //std::cout << std::setw(4) << output_offset;
          for (size_t kh=0; kh<weight_size[idx].d3; kh++) {
            for (size_t kw=0; kw<weight_size[idx].d2; kw++) {
              input_offset = (ow+kw) + input_fm_w * ((oh+kh) + input_fm_h * ic);
              weight_offset = kw + weight_size[idx].d2 * kh;
              in_data = *(in+input_offset);
              wgt_data = *(weight+weight_offset);
              //std::cout << *(out+output_offset) << " + " << in_data << " * " << wgt_data << std::endl;
              *(out+output_offset) += in_data * wgt_data;
            }
          }
          std::cout << std::setw(6) << *(out+output_offset);
        }
        std::cout << std::endl;
        weight_offset += weight_len;
      }
      std::cout << "Input Offset = " << input_offset << std::endl;
      input_offset += input_fm_len;
    }
  }
}

template <typename T>
void accelerator<T>::pooling(size_t idx) {
  T* out = wr_addr[idx];
  T* in = wr_addr[idx];
  T* weight = weight_addr[idx];
  std::cout << "Applying Pooling to Layer number " << idx << std::endl;
  size_t conv_out_w = rd_size[idx].d2 - weight_size[idx].d2+1;
  size_t conv_out_h = rd_size[idx].d3 - weight_size[idx].d3+1;
  size_t output_offset = 0;
  size_t input_offset = 0;
  size_t input_fm_w = conv_out_w;
  size_t input_fm_h = conv_out_h;
  size_t input_fm_len = input_fm_w * input_fm_h;

  size_t weight_offset = 0;
  size_t weight_len = ceil_a_by_b(wr_size[idx].d2 * wr_size[idx].d3, 4);

  T in_data, wgt_data, out_data, bias;

  //for (size_t oc=0; oc<wr_size[idx].d1;oc++) {
  for (size_t oc=0; oc<1;oc++) {
    std::cout << "Output Channel " << oc << std::endl;
    for (size_t ic=0; ic<rd_size[idx].d1; ic++) {
      bias = *(weight);
      weight += 4;
      std::cout << "Bias = " << bias << std::endl;
      for (size_t oh=0; oh<conv_out_h; oh++) {
        for (size_t ow=0; ow<conv_out_w; ow++) {
      //for (size_t oh=0; oh<1; oh++) {
        //for (size_t ow=0; ow<1; ow++) {
          output_offset = ow + input_fm_w * (oh + input_fm_h * ic);
          if (ic == 0)
            *(out+output_offset) = bias;
          //std::cout << std::setw(4) << output_offset;
          for (size_t kh=0; kh<weight_size[idx].d3; kh++) {
            for (size_t kw=0; kw<weight_size[idx].d2; kw++) {
              input_offset = (ow+kw) + input_fm_w * ((oh+kh) + input_fm_h * ic);
              weight_offset = kw + weight_size[idx].d2 * kh;
              in_data = *(in+input_offset);
              wgt_data = *(weight+weight_offset);
              //std::cout << *(out+output_offset) << " + " << in_data << " * " << wgt_data << std::endl;
              *(out+output_offset) += in_data * wgt_data;
            }
          }
          std::cout << std::setw(6) << *(out+output_offset);
        }
        std::cout << std::endl;
        weight_offset += weight_len;
      }
      std::cout << "Input Offset = " << input_offset << std::endl;
      input_offset += input_fm_len;
    }
  }
}


// ==============================================
// Functions for reading weights/inputs from file.
// Please change the following two functions
// according to your binary file.
// ==============================================

template <typename T>
void accelerator<T>::initialize_read_data_from_file(const char* filename) {
  std::cout << std::endl;
  std::cout << "Initializing inputs from binary file: " << filename << std::endl;
  std::cout << std::endl;
  for (int l=0; l<1; l++) {
    std::cout << "Input Addr: " << std::hex << rd_addr[l] << std::dec << std::endl;
    std::cout << "Input Dimensions: ";
    std::cout << rd_size[l].d0 << " x " <<
      rd_size[l].d1 << " x " <<
      rd_size[l].d2 << " x " <<
      rd_size[l].d3 << std::endl;

    size_t input_fm_width = rd_size[l].d2;
    size_t input_fm_height = rd_size[l].d3;
    size_t input_fm_channels = rd_size[l].d1;

    // We pad the width dimension according to number of PEs
    size_t padded_input_fm_width = ceil_a_by_b(input_fm_width, num_pe) * num_pe;

    for (size_t i=0; i<padded_input_fm_width; i++){
      
    }

    T* addr = rd_addr[l];
    size_t offset = 0;
    T value = 0;
    for (int ic=0; ic<input_fm_channels; ic++) {
      for (size_t w_count=0; w_count<padded_input_fm_width; w_count++) {
        for (size_t h_count=0; h_count<input_fm_height; h_count++) {
          offset = w_count + padded_input_fm_width * (h_count + input_fm_height * ic);
          if (w_count < input_fm_width) {
            // Change this according to your binary
            value = w_count+input_fm_width*(h_count);
          } else {
            value = 0;
          }
          *(addr+offset) = value;
        }
      }
    }

    size_t len = padded_input_fm_width * input_fm_height * input_fm_channels;
    cma_cache_clean((char*)addr, len);

  }
}

template <typename T>
void accelerator<T>::initialize_weights_from_file(const char* filename) {
  std::cout << std::endl;
  std::cout << "Initializing weights from binary file: " << filename << std::endl << std::endl;
  for (int l=0; l<num_layers; l++) {

    std::cout << "Weight Addr: " << std::hex << weight_addr[l] << std::dec << std::endl;
    std::cout << "Weight Dimensions: ";
    std::cout << weight_size[l].d0 << " x " <<
      weight_size[l].d1 << " x " <<
      weight_size[l].d2 << " x " <<
      weight_size[l].d3 << std::endl;

    size_t unpadded_len = weight_size[l].d2 * weight_size[l].d3;
    size_t padded_len = weight_size[l].d2 * weight_size[l].d3;

    int num_words_per_axi_width = 8 / sizeof(T);

    padded_len = num_words_per_axi_width + \
                 ceil_a_by_b(padded_len, num_words_per_axi_width) * num_words_per_axi_width;
    std::cout << "padded len = " << padded_len << std::endl;

    size_t len = weight_size[l].d0 * weight_size[l].d1 * padded_len;
    std::cout << "write data dimensions = " << len << std::endl;

    T* addr = weight_addr[l];

    size_t num_weights = weight_size[l].d0 * weight_size[l].d1;

    // Initialize Bias:
    for (size_t i=0; i<num_words_per_axi_width; i++)
      addr[i] = 0;
    // Initialize Weights:
    for (size_t i=0; i<padded_len-num_words_per_axi_width; i++){
      // Read from file
      if (i < unpadded_len) {
        addr[num_words_per_axi_width+i] = 0;
      }
      else {
        // Padding extra weights to zero
        addr[num_words_per_axi_width+i] = 0;
      }
    }
    std::cout << std::endl;

    cma_cache_clean((char*)addr, padded_len);
  }

}

template class accelerator<short>;
