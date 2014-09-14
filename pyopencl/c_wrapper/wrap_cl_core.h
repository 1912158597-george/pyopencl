// Interface between C and Python

// Types
typedef enum {
    KND_UNKNOWN,
    KND_SOURCE,
    KND_BINARY
} program_kind_type;

typedef struct {
    const char *routine;
    const char *msg;
    cl_int code;
    int other;
} error;

typedef enum {
    CLASS_NONE,
    CLASS_PLATFORM,
    CLASS_DEVICE,
    CLASS_KERNEL,
    CLASS_CONTEXT,
    CLASS_BUFFER,
    CLASS_PROGRAM,
    CLASS_EVENT,
    CLASS_COMMAND_QUEUE,
    CLASS_GL_BUFFER,
    CLASS_GL_RENDERBUFFER,
    CLASS_IMAGE,
    CLASS_SAMPLER
} class_t;

typedef struct {
    class_t opaque_class;
    const char *type;
    void *value;
    int dontfree;
} generic_info;


// Generic functions
int get_cl_version();
void free_pointer(void*);
void free_pointer_array(void**, uint32_t size);
void set_gc(int (*func)());
void set_deref(void (*func)(unsigned long));
int have_gl();

unsigned bitlog2(unsigned long v);
void populate_constants(void(*add)(const char*, const char*, long value));

// Platform
error *get_platforms(clobj_t **ptr_platforms, uint32_t *num_platforms);
error *platform__get_devices(clobj_t platform, clobj_t **ptr_devices,
                             uint32_t *num_devices, cl_device_type devtype);
// Context
error *create_context(clobj_t *ctx, const cl_context_properties *properties,
                      cl_uint num_devices, const clobj_t *ptr_devices);
error *context__get_supported_image_formats(clobj_t context, cl_mem_flags flags,
                                            cl_mem_object_type image_type,
                                            generic_info *out);
// Command Queue
error *create_command_queue(clobj_t *queue, clobj_t context, clobj_t device,
                            cl_command_queue_properties properties);
error *command_queue__finish(clobj_t queue);
error *command_queue__flush(clobj_t queue);
// Buffer
error *create_buffer(clobj_t *buffer, clobj_t context, cl_mem_flags flags,
                     size_t size, void *hostbuf);
// Memory Object
error *memory_object__release(clobj_t obj);
// Program
error *create_program_with_source(clobj_t *program, clobj_t context,
                                  const char *src);
error *create_program_with_binary(clobj_t *program, clobj_t context,
                                  cl_uint num_devices, const clobj_t *devices,
                                  char **binaries, size_t *binary_sizes);
error *program__build(clobj_t program, const char *options,
                      cl_uint num_devices, const clobj_t *devices);
error *program__kind(clobj_t program, int *kind);
error *program__get_build_info(clobj_t program, clobj_t device,
                               cl_program_build_info param, generic_info *out);
// Sampler
error *create_sampler(clobj_t *sampler, clobj_t context, int norm_coords,
                      cl_addressing_mode am, cl_filter_mode fm);
// Kernel
error *create_kernel(clobj_t *kernel, clobj_t program, const char *name);
error *kernel__set_arg_null(clobj_t kernel, cl_uint arg_index);
error *kernel__set_arg_mem(clobj_t kernel, cl_uint arg_index, clobj_t mem);
error *kernel__set_arg_sampler(clobj_t kernel, cl_uint arg_index,
                               clobj_t sampler);
error *kernel__set_arg_buf(clobj_t kernel, cl_uint arg_index,
                           const void *buffer, size_t size);
error *kernel__get_work_group_info(clobj_t kernel,
                                   cl_kernel_work_group_info param,
                                   clobj_t device, generic_info *out);
// Image
error *create_image_2d(clobj_t *image, clobj_t context, cl_mem_flags flags,
                       cl_image_format *fmt, size_t width, size_t height,
                       size_t pitch, void *buffer);
error *create_image_3d(clobj_t *image, clobj_t context, cl_mem_flags flags,
                       cl_image_format *fmt, size_t width, size_t height,
                       size_t depth, size_t pitch_x, size_t pitch_y,
                       void *buffer);
error *image__get_image_info(clobj_t image, cl_image_info param,
                             generic_info *out);
// Event
error *event__get_profiling_info(clobj_t event, cl_profiling_info param,
                                 generic_info *out);
error *event__wait(clobj_t event);
// enqueue_*
error *enqueue_nd_range_kernel(clobj_t *event, clobj_t queue,
                               clobj_t kernel, cl_uint work_dim,
                               const size_t *global_work_offset,
                               const size_t *global_work_size,
                               const size_t *local_work_size,
                               const clobj_t *wait_for, uint32_t num_wait_for);
error *enqueue_marker_with_wait_list(clobj_t *event, clobj_t queue,
                                     const clobj_t *wait_for,
                                     uint32_t num_wait_for);
error *enqueue_barrier_with_wait_list(clobj_t *event, clobj_t queue,
                                      const clobj_t *wait_for,
                                      uint32_t num_wait_for);
error *enqueue_marker(clobj_t *event, clobj_t queue);
error *enqueue_barrier(clobj_t queue);

error *enqueue_read_buffer(clobj_t *event, clobj_t queue, clobj_t mem,
                           void *buffer, size_t size, size_t device_offset,
                           const clobj_t *wait_for, uint32_t num_wait_for,
                           int is_blocking);
error *enqueue_copy_buffer(clobj_t *event, clobj_t queue, clobj_t src,
                           clobj_t dst, ptrdiff_t byte_count,
                           size_t src_offset, size_t dst_offset,
                           const clobj_t *wait_for, uint32_t num_wait_for);
error *enqueue_write_buffer(clobj_t *event, clobj_t queue, clobj_t mem,
                            const void *buffer, size_t size,
                            size_t device_offset, const clobj_t *wait_for,
                            uint32_t num_wait_for, int is_blocking);

error *enqueue_read_image(clobj_t *event, clobj_t queue, clobj_t mem,
                          size_t *origin, size_t *region, void *buffer,
                          size_t row_pitch, size_t slice_pitch,
                          const clobj_t *wait_for, uint32_t num_wait_for,
                          int is_blocking);
// CL Object
intptr_t clobj__int_ptr(clobj_t obj);
error *clobj__get_info(clobj_t obj, cl_uint param, generic_info *out);
void clobj__delete(clobj_t obj);

error *_from_int_ptr(clobj_t *ptr_out, intptr_t int_ptr_value, class_t);
