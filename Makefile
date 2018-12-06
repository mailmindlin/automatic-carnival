SOURCES := $(shell find . -name '*.c')

TARGETS = $(patsubst %.c,%.o,$(SOURCES))

CFLAGS += -Wall -g

all: a.out

a.out: $(TARGETS)
	$(CC) $(CFLAGS) $(TARGETS) -o a.out

%.o: %.c
	$(CC) $(CFLAGS) -MMD -MP -c $< -o $@

clean:
	rm $(TARGETS) $(patsubst %.c,%.d,$(SOURCES)) a.out
