
from pyopencl._cl import device_info, context_info, command_queue_info, Event, event_info, mem_info, Image, image_info, program_info, Kernel, ImageFormat, GLBuffer, kernel_info, sampler_info, Sampler, have_gl, _enqueue_read_image, _enqueue_write_image, GLTexture, channel_type, _enqueue_copy_image, _enqueue_copy_image_to_buffer, _enqueue_copy_buffer_to_image, _enqueue_write_buffer, _enqueue_copy_buffer, get_cl_header_version, _enqueue_read_buffer_rect, _enqueue_write_buffer_rect, _enqueue_copy_buffer_rect, RuntimeError, program_kind, mem_object_type, Error, platform_info, device_type, mem_flags, LogicError

import warnings

import os.path
current_directory = os.path.dirname(__file__)




from cffi import FFI
_ffi = FFI()
_cl_header = """

/* cl.h */
/* scalar types */
typedef int8_t		cl_char;
typedef uint8_t		cl_uchar;
typedef int16_t		cl_short;
typedef uint16_t	cl_ushort;
typedef int32_t		cl_int;
typedef uint32_t	cl_uint;
typedef int64_t		cl_long;
typedef uint64_t	cl_ulong;

typedef uint16_t        cl_half;
typedef float                   cl_float;
typedef double                  cl_double;


typedef struct _cl_platform_id *    cl_platform_id;
typedef struct _cl_device_id *      cl_device_id;
typedef struct _cl_context *        cl_context;
typedef struct _cl_command_queue *  cl_command_queue;
typedef struct _cl_mem *            cl_mem;
typedef struct _cl_program *        cl_program;
typedef struct _cl_kernel *         cl_kernel;
typedef struct _cl_event *          cl_event;
typedef struct _cl_sampler *        cl_sampler;

typedef cl_uint             cl_bool;                     /* WARNING!  Unlike cl_ types in cl_platform.h, cl_bool is not guaranteed to be the same size as the bool in kernels. */ 
typedef cl_ulong            cl_bitfield;
typedef cl_bitfield         cl_device_type;
typedef cl_uint             cl_platform_info;
typedef cl_uint             cl_device_info;
typedef cl_bitfield         cl_device_fp_config;
typedef cl_uint             cl_device_mem_cache_type;
typedef cl_uint             cl_device_local_mem_type;
typedef cl_bitfield         cl_device_exec_capabilities;
typedef cl_bitfield         cl_command_queue_properties;
typedef intptr_t            cl_device_partition_property;
typedef cl_bitfield         cl_device_affinity_domain;

typedef intptr_t            cl_context_properties;
typedef cl_uint             cl_context_info;
typedef cl_uint             cl_command_queue_info;
typedef cl_uint             cl_channel_order;
typedef cl_uint             cl_channel_type;
typedef cl_bitfield         cl_mem_flags;
typedef cl_uint             cl_mem_object_type;
typedef cl_uint             cl_mem_info;
typedef cl_bitfield         cl_mem_migration_flags;
typedef cl_uint             cl_image_info;
typedef cl_uint             cl_buffer_create_type;
typedef cl_uint             cl_addressing_mode;
typedef cl_uint             cl_filter_mode;
typedef cl_uint             cl_sampler_info;
typedef cl_bitfield         cl_map_flags;
typedef cl_uint             cl_program_info;
typedef cl_uint             cl_program_build_info;
typedef cl_uint             cl_program_binary_type;
typedef cl_int              cl_build_status;
typedef cl_uint             cl_kernel_info;
typedef cl_uint             cl_kernel_arg_info;
typedef cl_uint             cl_kernel_arg_address_qualifier;
typedef cl_uint             cl_kernel_arg_access_qualifier;
typedef cl_bitfield         cl_kernel_arg_type_qualifier;
typedef cl_uint             cl_kernel_work_group_info;
typedef cl_uint             cl_event_info;
typedef cl_uint             cl_command_type;
typedef cl_uint             cl_profiling_info;

/* cl_mem_flags - bitfield */
#define CL_MEM_READ_WRITE  ...
#define CL_MEM_WRITE_ONLY  ...
#define CL_MEM_READ_ONLY  ...
#define CL_MEM_USE_HOST_PTR  ...
#define CL_MEM_ALLOC_HOST_PTR  ...
#define CL_MEM_COPY_HOST_PTR  ...
#define CL_MEM_HOST_WRITE_ONLY  ...
#define CL_MEM_HOST_READ_ONLY  ...
#define CL_MEM_HOST_NO_ACCESS  ...


"""

with open(os.path.join(current_directory, 'wrap_cl_core.h')) as _f:
    _wrap_cl_header = _f.read()

_ffi.cdef('%s\n%s' % (_cl_header, _wrap_cl_header))
print current_directory
_lib = _ffi.verify(
    """
    #include <wrap_cl.h>
    """,
    include_dirs=[os.path.join(current_directory, "../src/c_wrapper/")],
    library_dirs=[current_directory],
    libraries=["wrapcl", "OpenCL"])

class PP(object):
    def __init__(self, ptr):
        self.ptr = ptr
        self.size = _ffi.new('uint32_t *')

    def __getitem__(self, key):
        return self.ptr[0].__getitem__(key)

    def __iter__(self):
        for i in xrange(self.size[0]):
            yield self[i]

    def __del__(self):
        _lib.freem(self.ptr[0])

class CLRuntimeError(RuntimeError):
    def __init__(self, routine, code, msg=""):
        super(CLRuntimeError, self).__init__(msg)
        self.routine = routine
        self.code = code

        
# plats = _ffi.new("void**")
# print _lib.get_platforms(plats)
# print _ffi.cast('int**', plats)[0][1]
# exit()



# _platform_info_constants = {
#     'PROFILE': _lib.CL_PLATFORM_PROFILE,
#     'VERSION': _lib.CL_PLATFORM_VERSION,
#     'NAME': _lib.CL_PLATFORM_NAME,
#     'VENDOR': _lib.CL_PLATFORM_VENDOR,
# }

# # re-implementation
# platform_info = type("platform_info", (NOINIT,), _platform_info_constants)

# _device_type_constants = {
#     'DEFAULT': _lib.CL_DEVICE_TYPE_DEFAULT,
#     'CPU': _lib.CL_DEVICE_TYPE_CPU,
#     'GPU': _lib.CL_DEVICE_TYPE_GPU,
#     'ACCELERATOR': _lib.CL_DEVICE_TYPE_ACCELERATOR,
#     'ALL': _lib.CL_DEVICE_TYPE_ALL,
#     }
# if _CL_VERSION >= (1, 2):
#     _device_type_constants['CUSTOM'] = _lib.CL_DEVICE_TYPE_CUSTOM

# # re-implementation
# device_type = type("device_type", (NOINIT,), _device_type_constants)

# _mem_flags_constants = {
#     'READ_WRITE': _lib.CL_MEM_READ_WRITE, 
#     'WRITE_ONLY': _lib.CL_MEM_WRITE_ONLY, 
#     'READ_ONLY': _lib.CL_MEM_READ_ONLY, 
#     'USE_HOST_PTR': _lib.CL_MEM_USE_HOST_PTR, 
#     'ALLOC_HOST_PTR': _lib.CL_MEM_ALLOC_HOST_PTR, 
#     'COPY_HOST_PTR': _lib.CL_MEM_COPY_HOST_PTR,
#     # TODO_PLAT
#     # #ifdef cl_amd_device_memory_flags
#     #     'USE_PERSISTENT_MEM_AMD': _lib.CL_MEM_USE_PERSISTENT_MEM_AMD, 
#     # #endif
#     }
# if _CL_VERSION >= (1, 2):
#     _mem_flags_constants.update({
#         'HOST_WRITE_ONLY': _lib.CL_MEM_HOST_WRITE_ONLY, 
#         'HOST_READ_ONLY': _lib.CL_MEM_HOST_READ_ONLY, 
#         'HOST_NO_ACCESS': _lib.CL_MEM_HOST_NO_ACCESS,
#     })

# # re-implementation
# mem_flags = type("mem_flags", (NOINIT,), _mem_flags_constants)

class EQUALITY_TESTS(object):
    def __eq__(self, other):
        return hash(self) == hash(other)

class Device(EQUALITY_TESTS):
    def __init__(self):
        pass

    def __hash__(self):
        return _lib.device__hash(self.ptr)

    # todo: __del__

    def get_info(self, param):
        if param == 4145:
            return self.__dict__["platform"] # TODO HACK
        value = _ffi.new('char **')
        _lib.device__get_info(self.ptr, param, value)
        return _ffi.string(value[0])

def _create_device(ptr):
    device = Device()
    device.ptr = ptr
    return device

def _parse_context_properties(properties):
    props = []
    if properties is None:
        return _ffi.NULL

    for prop_tuple in properties:
        if len(prop_tuple) != 2:
            raise CLRuntimeError("Context", _lib.CL_INVALID_VALUE, "property tuple must have length 2")
        prop, value = prop_tuple
        props.append(prop)
        if prop == _lib.CL_CONTEXT_PLATFORM:
            props.append(_ffi.cast('cl_context_properties', value.data()))
            
        else: # TODO_PLAT CL_WGL_HDC_KHR and morecc
            raise CLRuntimeError("Context", _lib.CL_INVALID_VALUE, "invalid context property")
    props.append(0)
    return _ffi.new('cl_context_properties[]', props)

        
class Context(object):
    def __init__(self, devices=None, properties=None, dev_type=None):
        c_props = _parse_context_properties(properties)
        status_code = _ffi.new('cl_int *')
        
        # from device list
        if devices is not None:
            if dev_type is not None:
                raise CLRuntimeError("Context", _lib.CL_INVALID_VALUE, "one of 'devices' or 'dev_type' must be None")
            ptr_devices = _ffi.new('cl_device_id[]', [device.ptr for device in devices])
            ptr_ctx = _ffi.new('void **')
            _lib._create_context(ptr_ctx, c_props, len(ptr_devices), _ffi.cast('void**', ptr_devices))
            
        else: # from dev_type
            raise NotImplementedError()

        self.ptr = ptr_ctx[0]

    def get_info(self, param):
        return 'TODO'

class CommandQueue(object):
    def __init__(self, context, device=None, properties=None):
        if properties is None:
            properties = 0
        ptr_command_queue = _ffi.new('void **')
        _lib._create_command_queue(ptr_command_queue, context.ptr, _ffi.NULL if device is None else device.ptr, properties)
        self.ptr = ptr_command_queue[0]

    def get_info(self, param):
        print param
        raise NotImplementedError()

class MemoryObjectHolder(object):
    def get_info(self, param):
        info = _ffi.new('generic_info *')
        _lib.memory_object_holder__get_info(self.ptr, param, info)
        return _generic_info_to_python(info)

class MemoryObject(MemoryObjectHolder):
    pass
        
class Buffer(MemoryObjectHolder):
    def __init__(self, context, flags, size=0, hostbuf=None):
        if hostbuf is not None and not (flags & (_lib.CL_MEM_USE_HOST_PTR | _lib.CL_MEM_COPY_HOST_PTR)):
            warnings.warn("'hostbuf' was passed, but no memory flags to make use of it.")
        c_hostbuf = _ffi.NULL
        if hostbuf is not None:
            # todo: buffer protocol; for now hostbuf is assumed to be a numpy array
            c_hostbuf = _ffi.cast('void *', hostbuf.ctypes.data)
            hostbuf_size = hostbuf.nbytes
            if size > hostbuf_size:
                raise CLRuntimeError("Buffer", _lib.CL_INVALID_VALUE, "specified size is greater than host buffer size")
            if size == 0:
                size = hostbuf_size

        ptr_buffer = _ffi.new('void **')
        _lib._create_buffer(ptr_buffer, context.ptr, flags, size, c_hostbuf)
        self.ptr = ptr_buffer[0]

class _Program(object):
    def __init__(self, *args):
        if len(args) == 2:
            self._init_source(*args)
        else:
            self._init_binary(*args)

    def int_ptr(self):
        raise NotImplementedError()

    def from_int_ptr(self, int_ptr_value):
        raise NotImplementedError()
            
    def _init_source(self, context, src):
        ptr_program = _ffi.new('void **')
        _lib._create_program_with_source(ptr_program, context.ptr, _ffi.new('char[]', src))
        self.ptr = ptr_program[0]

    def _init_binary(self, context, devices, binaries):
        if len(devices) != len(binaries):
            raise CLRuntimeError("create_program_with_binary", _lib.CL_INVALID_VALUE, "device and binary counts don't match")
            
        ptr_program = _ffi.new('void **')
        ptr_devices = _ffi.new('void*[]', [device.ptr for device in devices])
        ptr_binaries = _ffi.new('char*[]', len(binaries))
        for i, binary in enumerate(binaries):
            ptr_binaries[i] = _ffi.new('char[]', binary)
        _lib._create_program_with_binary(ptr_program, context.ptr, len(ptr_devices), ptr_devices, len(ptr_binaries), ptr_binaries)
        self.ptr = ptr_program[0]

    def kind(self):
        kind = _ffi.new('int *')
        _lib.program__kind(self.ptr, kind)
        return kind[0]

    def _build(self, options=None, devices=None):
        if devices is None: raise NotImplementedError()
        # TODO: if devices is None, create them
        if options is None:
            options = ""
        ptr_devices = _ffi.new('void*[]', [device.ptr for device in devices])
        _lib.program__build(self.ptr, _ffi.new('char[]', options), len(ptr_devices), _ffi.cast('void**', ptr_devices))

    def get_info(self, param):
        if param == program_info.DEVICES:
            # todo: refactor, same code as in get_devices 
            devices = PP(_ffi.new('void**'))
            _lib.program__get_info__devices(self.ptr, devices.ptr, devices.size)
            result = []
            for i in xrange(devices.size[0]):
                # TODO why is the cast needed? 
                device_ptr = _ffi.cast('void**', devices.ptr[0])[i]
                result.append(_create_device(device_ptr))
            return result
        elif param == program_info.BINARIES:
            # TODO possible memory leak? the char arrays might not be freed
            ptr_binaries = PP(_ffi.new('char***'))
            _lib.program__get_info__binaries(self.ptr, ptr_binaries.ptr, ptr_binaries.size)
            return map(_ffi.string, ptr_binaries)
        print param
        raise NotImplementedError()
        
class Platform(object):
    def __init__(self):
        pass

    # todo: __del__

    def get_info(self, param):
        value = _ffi.new('char **')
        _lib.platform__get_info(self.ptr, param, value)
        return _ffi.string(value[0])
    
    def get_devices(self, device_type=device_type.ALL):
        devices = PP(_ffi.new('void**'))
        _lib.platform__get_devices(self.ptr, devices.ptr, devices.size, device_type)
        result = []
        for i in xrange(devices.size[0]):
            # TODO why is the cast needed? 
            device_ptr = _ffi.cast('void**', devices.ptr[0])[i]
            result.append(_create_device(device_ptr))
        # TODO remove, should be done via get_info(PLATFORM)
        for r in result:
            r.__dict__["platform"] = self
        return result

def _create_platform(ptr):
    platform = Platform()
    platform.ptr = ptr
    return platform

def _generic_info_to_python(info):
    for type_ in ('cl_uint',
                  'cl_mem_object_type',
                  ):
        if info.type == getattr(_lib, 'generic_info_type_%s' % type_):
            return getattr(info.value, '_%s' % type_)
    raise NotImplementedError(info.type)

class Kernel(object):
    def __init__(self, program, name):
        ptr_kernel = _ffi.new('void **')
        _lib._create_kernel(ptr_kernel, program.ptr, name)
        self.ptr = ptr_kernel[0]

    def get_info(self, param):
        info = _ffi.new('generic_info *')
        _lib.kernel__get_info(self.ptr, param, info)
        return _generic_info_to_python(info)
        #raise NotImplementedError()

    def set_arg(self, arg_index, arg):
        if isinstance(arg, Buffer):
            _lib.kernel__set_arg_mem_buffer(self.ptr, arg_index, arg.ptr)
        else:
            raise NotImplementedError()
    
def get_platforms():
    platforms = PP(_ffi.new('void**'))
    _lib.get_platforms(platforms.ptr, platforms.size)
    result = []
    for i in xrange(platforms.size[0]):
        # TODO why is the cast needed? 
        platform_ptr = _ffi.cast('void**', platforms.ptr[0])[i]
        result.append(_create_platform(platform_ptr))
        
    return result

class Event(object):
    def __init__(self):
        pass

    def get_info(self, param):
        print param
        raise NotImplementedError()
    
def _create_event(ptr):
    event = Event()
    event.ptr = ptr
    return event


def enqueue_nd_range_kernel(queue, kernel, global_work_size, local_work_size, global_work_offset=None, wait_for=None, g_times_l=False):
    if wait_for is not None:
        raise NotImplementedError("wait_for")
    work_dim = len(global_work_size)
    
    if local_work_size is not None:
        if g_times_l:
            work_dim = max(work_dim, len(local_work_size))
        elif work_dim != len(local_work_size):
            raise CLRuntimeError("enqueue_nd_range_kernel", _lib.CL_INVALID_VALUE,
                                 "global/local work sizes have differing dimensions")
        
        local_work_size = list(local_work_size)
        
        if len(local_work_size) < work_dim:
            local_work_size.extend([1] * (work_dim - len(local_work_size)))
        if len(global_work_size) < work_dim:
            global_work_size.extend([1] * (work_dim - len(global_work_size)))
            
    elif g_times_l:
        for i in xrange(work_dim):
            global_work_size[i] *= local_work_size[i]

    if global_work_offset is not None:
        raise NotImplementedError("global_work_offset")

    c_global_work_offset = _ffi.NULL
    c_global_work_size = _ffi.new('const size_t[]', global_work_size)
    if local_work_size is None:
        c_local_work_size = _ffi.NULL
    else:
        c_local_work_size = _ffi.new('const size_t[]', local_work_size)

    ptr_event = _ffi.new('void **')
    _lib._enqueue_nd_range_kernel(
        ptr_event,
        queue.ptr,
        kernel.ptr,
        work_dim,
        c_global_work_offset,
        c_global_work_size,
        c_local_work_size
    )
    return _create_event(ptr_event[0])

def _enqueue_read_buffer(cq, mem, buf, device_offset=0, is_blocking=True):
    # assume numpy
    c_buf = _ffi.cast('void *', buf.ctypes.data)
    size = buf.nbytes
    ptr_event = _ffi.new('void **')
    _lib._enqueue_read_buffer(
        ptr_event,
        cq.ptr,
        mem.ptr,
        c_buf,
        size,
        device_offset,
        bool(is_blocking)
    )
    return _create_event(ptr_event[0])



