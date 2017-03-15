CC = arm-xilinx-eabi-gcc
CFLAGS = -O3 -Wall -I./lib -I./lib/bsp/include/ -c
LDFLAGS = -Wl,-T -Wl,./lib/lscript.ld -L ./lib
LIBS = -Wl,--start-group,-lxil,-lgcc,-lc,-lm,--end-group

SRCDIR = src
LIBDIR = lib
OBJDIR = obj
BINDIR = bin
SRCFILES := $(wildcard $(SRCDIR)/*.c)
LIBFILES := $(wildcard $(LIBDIR)/*.c)
SRC_OBJS := $(SRCFILES:$(SRCDIR)/%.c=$(OBJDIR)/%.o)
LIB_OBJS := $(LIBFILES:$(LIBDIR)/%.c=$(OBJDIR)/%.o)
ALL_OBJS := $(LIB_OBJS) $(SRC_OBJS)
EXECUTABLE=arm_loopback.elf


# All Target
all: $(BINDIR)/$(EXECUTABLE)

$(BINDIR)/$(EXECUTABLE): $(ALL_OBJS)
	@echo Building target: $@
	@echo Invoking: ARM gcc linker
	$(CC) $(LDFLAGS) $(ALL_OBJS) -o $@ $(LIBS)
	@echo Finished building target: $@
	@echo ' '

$(SRC_OBJS):$(OBJDIR)/%.o:$(SRCDIR)/%.c
	@echo Building object: $@
	@echo Invoking: ARM gcc compiler
	$(CC) $(CFLAGS) $< -o $@
	@echo Finished building object files: $@
	@echo ' '

$(LIB_OBJS):$(OBJDIR)/%.o:$(LIBDIR)/%.c
	@echo Building object: $@
	@echo Invoking: ARM gcc compiler
	$(CC) $(CFLAGS) $< -o $@
	@echo Finished building object files: $@
	@echo ' '

clean:
	@echo Cleaning up...
	rm -rf $(OBJDIR)/*.o *.elf
	@echo ' '
