#include <stdio.h>
#include "platform.h"
#include "xil_types.h"
#include "xil_printf.h"
#include "xil_cache.h"

#define AXI_GP0_MASTER_BASE_ADDR (u16*)0x43C00000
#define AXI_HP0_RD_BASE_ADDR     (u16*)0x00000000
#define AXI_HP0_WR_BASE_ADDR     (u16*)0x02000000

#define NUM_PE          4
#define TEST_VEC_LEN    64

int main () {
	init_platform();
	Xil_DCacheDisable();

	xil_printf ("==================================================\n\r ");
	xil_printf ("Loopback Test\n\r ");
	volatile u32 * control_master = AXI_GP0_MASTER_BASE_ADDR;
	volatile u16 * rd_address   = *(control_master + 2);
	volatile u16 * wr_address   = *(control_master + 3);

  u16 i;

	for (i=0; i<TEST_VEC_LEN; i++) {
		*(wr_address+i) = 1;
	}
	xil_printf("    Done!\n\r ");

  xil_printf ("Initializing Read location\n\r ");
  for (i=0; i<TEST_VEC_LEN; i++) {
	  *(rd_address+i) = i;
    xil_printf("Address: %6x\tData: %6d\n\r ", rd_address+i, *(rd_address+i));
  }
	xil_printf("    Done!\n\r ");
  xil_printf ("Initializing Write location\n\r ");
  for (i=0; i<TEST_VEC_LEN; i++) {
	  *(wr_address+i) = -1;
  }
	xil_printf("    Done!\n\r ");

	xil_printf("Invoking the accelerator\n\r ");
	*(control_master+0) = 1 - *(control_master+0);
	xil_printf("Waiting for the accelerator to finish processing\n\r ");
	sleep(1);
	while (*(control_master+1) != 1) {
		sleep(5);
	}

  xil_printf ("Read_finished: %d\n\r ", *(control_master+2));
  xil_printf ("processing_finished: %d\n\n\r ", *(control_master+3));
  xil_printf ("total_cycles : %d\n\r ", *(control_master+4));
  xil_printf ("rd_cycles    : %d\n\r ", *(control_master+5));
  xil_printf ("pr_cycles    : %d\n\r ", *(control_master+6));
  xil_printf ("wr_cycles    : %d\n\r ", *(control_master+7));

	xil_printf("    Done!\n\r ");
  xil_printf("Verifying results \n\r ");
  u16 count = 0;

  xil_printf ("Expected output:\n\r ");
	for (i=0; i<TEST_VEC_LEN; i++) {
    xil_printf("Address: %6x\tData: %6x\n\r ", wr_address+i, *(rd_address+i));
	}
  xil_printf("\n\r ");

  xil_printf ("Received output:\n\r ");
	for (i=0; i<TEST_VEC_LEN; i++) {
    xil_printf("Address: %6x\tData: %6x\n\r ", wr_address+i, *(wr_address+i));
    count += *(rd_address+i) != *(wr_address+i);
	}
  xil_printf("\n\r ");

  if (count > 0) {
      xil_printf ("Results : Failed\n\r ");
  }
  else {
      xil_printf ("Results : Passed\n\r ");
  }
    xil_printf ("total_cycles : %d\n\r ", *(control_master+4));
    xil_printf ("rd_cycles    : %d\n\r ", *(control_master+5));
    xil_printf ("pr_cycles    : %d\n\r ", *(control_master+6));
    xil_printf ("wr_cycles    : %d\n\r ", *(control_master+7));
	xil_printf ("==================================================\n\r ");

	cleanup_platform();
	return 0;
}

