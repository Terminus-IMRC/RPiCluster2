.PHONY: all
all:

SRCS := main.c
MCU := attiny13a
AVRDUDE_PROGRAMMER := ft232r
AVRDUDE_PORT := ft0
AVRDUDE_PARTNO := t13
# Search for an appropriate one if this baud rate fails to communiate with AVR.
AVRDUDE_BAUDRATE := 19200

TARGET_ARCH := -mmcu=$(MCU)
CFLAGS += -pipe -W -Wall -Wextra -O3
LDLIBS +=

FLASH_ELF := flash.elf
FLASH_ELF_IHEX := $(patsubst %.elf, %.elf.ihex, $(filter %.elf, $(FLASH_ELF)))
OBJS := $(patsubst %.c, %.c.o, $(filter %.c, $(SRCS)))

CC := avr-gcc
OBJCOPY := avr-objcopy
AVRDUDE := avrdude
RM := rm -rf

LINK.o = $(CC) $(CFLAGS) $(CPPFLAGS) $(TARGET_ARCH)
COMPILE.c = $(CC) $(CFLAGS) $(CPPFLAGS) $(TARGET_ARCH) -c

all: build
#all: burn

.PHONY: burn
burn: $(FLASH_ELF_IHEX)
	$(AVRDUDE) -c "$(AVRDUDE_PROGRAMMER)" -P "$(AVRDUDE_PORT)" -p "$(AVRDUDE_PARTNO)" -B "$(AVRDUDE_BAUDRATE)" -U "flash:w:$^:i"

.PHONY: build
build: $(FLASH_ELF_IHEX)

$(FLASH_ELF_IHEX): $(FLASH_ELF)
	$(OBJCOPY) -j .text -j .data -I elf32-avr -O ihex "$<" "$@"

$(FLASH_ELF): $(OBJS)
	$(LINK.o) $(OBJS) $(LDLIBS) -o "$@"

%.c.o: %.c
	$(COMPILE.c) "$<" -o "$@"

.PHONY: clean
clean:
	$(RM) $(FLASH_ELF_IHEX)
	$(RM) $(FLASH_ELF)
	$(RM) $(OBJS)
