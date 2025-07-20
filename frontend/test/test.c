#include <stddef.h>
#include <string.h>

#include "./monitor.h"

// UTILITY: Function with utility access
UTILITY
void log_event(const char *msg);

// USER: Function with global memory access
USER
void admin_override(void *data);

// OPAQUE: Argument is a pointer whose memory won't be copied
void send_secret(OPAQUE void *ptr);

// STRING: Argument memory size inferred with strlen
void print_msg(STRING char *msg);

// LEN(2), SIZE(3): Argument size inferred from later integer arguments
void copy_buf(LEN(2) char *buf, int len, SIZE(3) int size);

// SHARED: Global variable accessible across compartments
SHARED int shared_state;

// CUSTOM: Entire function uses custom bridge implementation (e.g., custom_memcpy_custom)
CUSTOM
void custom_memcpy(void *dest, void *src, int len);

