from pyopencl._cl import PooledBuffer, MemoryPool
from _cffi import _get_lib
import warnings


_ffi, _lib = _get_lib()
bitlog2 = _lib.bitlog2

class _CArray(object):
    def __init__(self, ptr):
        self.ptr = ptr
        self.size = _ffi.new('uint32_t *')

    def __del__(self):
        if self.ptr != _ffi.NULL:
            _lib._free(self.ptr[0])

    def __getitem__(self, key):
        return self.ptr[0].__getitem__(key)

    def __iter__(self):
        for i in xrange(self.size[0]):
            yield self[i]

class _CArrays(_CArray):
    def __del__(self):
        _lib._free2(_ffi.cast('void**', self.ptr[0]), self.size[0])
        super(_CArrays, self).__del__()

class _NoInit(object):
    def __init__(self):
        raise RuntimeError("This class cannot be instantiated.")

def get_cl_header_version():
    v = _lib.get_cl_version()
    return (v >> (3*4),
            (v >> (1*4)) & 0xff)



# {{{ expose constants classes like platform_info, device_type, ...
_constants = {}
@_ffi.callback('void(const char*, const char* name, long value)')
def _constant_callback(type_, name, value):
    s_type = _ffi.string(type_)
    _constants.setdefault(s_type, {})
    _constants[s_type][_ffi.string(name)] = value
_lib.populate_constants(_constant_callback)

for type_, d in _constants.iteritems():
    locals()[type_] = type(type_, (_NoInit,), d)
# }}}


# {{{ exceptions

class Error(Exception):
    def __init__(self, routine, code, msg=""):
        self.routine = routine
        self.code = code
        self.what = msg
        super(Error, self).__init__(self, msg)

class MemoryError(Error):
    pass
class LogicError(Error):
    pass
class RuntimeError(Error):
    pass

def _handle_error(error):
    if error == _ffi.NULL:
        return
    if error.other == 1:
        # non-pyopencl exceptions are handled here
        import exceptions
        e = exceptions.RuntimeError(_ffi.string(error.msg))
        _lib._free(error.msg)
        _lib._free(error)
        raise e
    if error.code == status_code.MEM_OBJECT_ALLOCATION_FAILURE:
        klass = MemoryError
    elif error.code <= status_code.INVALID_VALUE:
        klass = LogicError
    elif status_code.INVALID_VALUE < error.code < status_code.SUCCESS:
        klass = RuntimeError
    else:
        klass = Error
    e = klass(_ffi.string(error.routine), error.code, _ffi.string(error.msg))
    _lib._free(error.routine)
    _lib._free(error.msg)
    _lib._free(error)
    raise e
# }}}

class _Common(object):
    ptr = _ffi.NULL
    
    @classmethod
    def _c_class_type(cls):
        return getattr(_lib, 'CLASS_%s' % cls._id.upper())

    def __del__(self):
        _lib._delete(self.ptr, self._c_class_type())

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __hash__(self):
        return _lib._hash(self.ptr, self._c_class_type())

    def get_info(self, param):
        info = _ffi.new('generic_info *')
        _handle_error(_lib._get_info(self.ptr, self._c_class_type(), param, info))
        return _generic_info_to_python(info)

    @property
    def int_ptr(self):
        return _lib._int_ptr(self.ptr, self._c_class_type())

    @classmethod
    def from_int_ptr(cls, int_ptr_value):
        ptr = _ffi.new('void **')
        _lib._from_int_ptr(ptr, int_ptr_value, getattr(_lib, 'CLASS_%s' % cls._id.upper()))
        #getattr(_lib, '%s__from_int_ptr' % cls._id)(ptr, int_ptr_value)
        return _create_instance(cls, ptr[0])

class Device(_Common):
    _id = 'device'

    # todo: __del__

    def get_info(self, param):
        return super(Device, self).get_info(param)

def _parse_context_properties(properties):
    props = []
    if properties is None:
        return _ffi.NULL

    for prop_tuple in properties:
        if len(prop_tuple) != 2:
            raise RuntimeError("Context", status_code.INVALID_VALUE, "property tuple must have length 2")
        prop, value = prop_tuple
        if prop is None:
            raise RuntimeError("Context", status_code.INVALID_VALUE, "invalid context property")

        props.append(prop)
        if prop == context_properties.PLATFORM:
            props.append(value.int_ptr)
        elif prop == getattr(context_properties, "WGL_HDC_KHR"): # TODO if _WIN32? Why?
            props.append(value)
        elif prop in [getattr(context_properties, key, None) for key in (
                'CONTEXT_PROPERTY_USE_CGL_SHAREGROUP_APPLE',
                'GL_CONTEXT_KHR',
                'EGL_DISPLAY_KHR',
                'GLX_DISPLAY_KHR',
                'CGL_SHAREGROUP_KHR',
                )]:
            # TODO: without ctypes?
            import ctypes
            val = (ctypes.cast(value, ctypes.c_void_p)).value
            if val is None:
                raise LogicError("Context", status_code.INVALID_VALUE, "You most likely have not initialized OpenGL properly.")
            props.append(val)
        else:
            raise RuntimeError("Context", status_code.INVALID_VALUE, "invalid context property")
    props.append(0)
    return _ffi.new('intptr_t[]', props)


class Context(_Common):
    _id = 'context'

    def __init__(self, devices=None, properties=None, dev_type=None):
        c_props = _parse_context_properties(properties)
        status_code = _ffi.new('cl_int *')

        # from device list
        if devices is not None:
            if dev_type is not None:
                raise RuntimeError("Context", status_code.INVALID_VALUE, "one of 'devices' or 'dev_type' must be None")
            ptr_devices = _ffi.new('void*[]', [device.ptr for device in devices])
            ptr_ctx = _ffi.new('void **')
            _handle_error(_lib._create_context(ptr_ctx, c_props, len(ptr_devices), _ffi.cast('void**', ptr_devices)))

        else: # from dev_type
            raise NotImplementedError()

        self.ptr = ptr_ctx[0]

class CommandQueue(_Common):
    _id = 'command_queue'
    def __init__(self, context, device=None, properties=None):
        if properties is None:
            properties = 0
        ptr_command_queue = _ffi.new('void **')
        _handle_error(_lib._create_command_queue(ptr_command_queue, context.ptr, _ffi.NULL if device is None else device.ptr, properties))
        self.ptr = ptr_command_queue[0]

class MemoryObjectHolder(_Common):
    pass

class MemoryObject(MemoryObjectHolder):
    pass

class Buffer(MemoryObject):
    _id = 'buffer'

    @classmethod
    def _c_buffer_from_obj(cls, obj):
        # assume numpy array for now
        return _ffi.cast('void *', obj.__array_interface__['data'][0]), obj.nbytes

    def __init__(self, context, flags, size=0, hostbuf=None):
        if hostbuf is not None and not (flags & (mem_flags.USE_HOST_PTR | mem_flags.COPY_HOST_PTR)):
            warnings.warn("'hostbuf' was passed, but no memory flags to make use of it.")
        c_hostbuf = _ffi.NULL
        if hostbuf is not None:
            c_hostbuf, hostbuf_size = self._c_buffer_from_obj(hostbuf)
            if size > hostbuf_size:
                raise RuntimeError("Buffer", status_code.INVALID_VALUE, "specified size is greater than host buffer size")
            if size == 0:
                size = hostbuf_size

        ptr_buffer = _ffi.new('void **')
        _handle_error(_lib._create_buffer(ptr_buffer, context.ptr, flags, size, c_hostbuf))
        self.ptr = ptr_buffer[0]

class _Program(_Common):
    _id = 'program'
    def __init__(self, *args):
        if len(args) == 2:
            self._init_source(*args)
        else:
            self._init_binary(*args)

    def _init_source(self, context, src):
        ptr_program = _ffi.new('void **')
        _handle_error(_lib._create_program_with_source(ptr_program, context.ptr, _ffi.new('char[]', src)))
        self.ptr = ptr_program[0]

    def _init_binary(self, context, devices, binaries):
        if len(devices) != len(binaries):
            raise RuntimeError("create_program_with_binary", status_code.INVALID_VALUE, "device and binary counts don't match")

        ptr_program = _ffi.new('void **')
        ptr_devices = _ffi.new('void*[]', [device.ptr for device in devices])
        ptr_binaries = [_ffi.new('char[%i]' % len(binary), binary) for binary in binaries]
        binary_sizes = _ffi.new('size_t[]', map(len, binaries))

        _handle_error(_lib._create_program_with_binary(
            ptr_program,
            context.ptr,
            len(ptr_devices),
            ptr_devices,
            len(ptr_binaries),
            _ffi.new('char*[]', ptr_binaries),
            binary_sizes))

        self.ptr = ptr_program[0]

    def kind(self):
        kind = _ffi.new('int *')
        _handle_error(_lib.program__kind(self.ptr, kind))
        return kind[0]

    def _build(self, options=None, devices=None):
        if options is None:
            options = ""
        #if devices is None: devices = self.get_info(0x1163)
        if devices is None:
            num_devices = 0
            ptr_devices = _ffi.NULL
        else:
            ptr_devices = _ffi.new('void*[]', [device.ptr for device in devices])
            num_devices = len(devices)

        _handle_error(_lib.program__build(self.ptr, _ffi.new('char[]', options), num_devices, _ffi.cast('void**', ptr_devices)))


    def get_build_info(self, device, param):
        info = _ffi.new('generic_info *')
        _handle_error(_lib.program__get_build_info(self.ptr, device.ptr, param, info))
        return _generic_info_to_python(info)

class Platform(_Common):
    _id = 'platform'
    # todo: __del__

    def get_devices(self, device_type=device_type.ALL):
        devices = _CArray(_ffi.new('void**'))
        _handle_error(_lib.platform__get_devices(self.ptr, devices.ptr, devices.size, device_type))
        result = []
        for i in xrange(devices.size[0]):
            # TODO why is the cast needed? 
            device_ptr = _ffi.cast('void**', devices.ptr[0])[i]
            result.append(_create_instance(Device, device_ptr))
        return result

def _generic_info_to_python(info):
    type_ = _ffi.string(info.type)
    value = _ffi.cast(type_, info.value)
    if info.opaque_class != _lib.CLASS_NONE:
        klass = {
            _lib.CLASS_PLATFORM: Platform,
            _lib.CLASS_DEVICE: Device,
            _lib.CLASS_KERNEL: Kernel, 
            _lib.CLASS_CONTEXT: Context,
            _lib.CLASS_BUFFER: Buffer,
            _lib.CLASS_PROGRAM: _Program, 
            _lib.CLASS_EVENT: Event,
            _lib.CLASS_COMMAND_QUEUE: CommandQueue
            }[info.opaque_class]

        def ci(ptr):
            ins = _create_instance(klass, ptr)
            if info.opaque_class == _lib.CLASS_PROGRAM: # HACK?
                from . import Program
                return Program(ins)
            return ins

        if type_.endswith(']'):
            ret = map(ci, value)
            _lib._free(info.value)
            return ret
        else:
            return ci(value)
    if type_ == 'char*':
        ret = _ffi.string(value)
    elif type_.startswith('char*['):
        ret = map(_ffi.string, value)
        _lib._free2(info.value, len(value))
    elif type_.endswith(']'):
        if type_.startswith('char['):
            ret = ''.join(a[0] for a in value)
        elif type_.startswith('generic_info['):
            ret = list(map(_generic_info_to_python, value))
        else:
            ret = list(value)
    else:
        ret = value[0]
    if info.dontfree == 0:
        _lib._free(info.value)
    return ret

class Kernel(_Common):
    _id = 'kernel'

    def __init__(self, program, name):
        ptr_kernel = _ffi.new('void **')
        _handle_error(_lib._create_kernel(ptr_kernel, program.ptr, name))
        self.ptr = ptr_kernel[0]

    def set_arg(self, arg_index, arg):
        if isinstance(arg, Buffer):
            _handle_error(_lib.kernel__set_arg_mem_buffer(self.ptr, arg_index, arg.ptr))
        else:
            raise NotImplementedError()

    def get_work_group_info(self, param, device):
        info = _ffi.new('generic_info *')
        _handle_error(_lib.kernel__get_work_group_info(self.ptr, param, device.ptr, info))
        return _generic_info_to_python(info)


def get_platforms():
    platforms = _CArray(_ffi.new('void**'))
    _handle_error(_lib.get_platforms(platforms.ptr, platforms.size))
    result = []
    for i in xrange(platforms.size[0]):
        # TODO why is the cast needed? 
        platform_ptr = _ffi.cast('void**', platforms.ptr[0])[i]
        result.append(_create_instance(Platform, platform_ptr))

    return result

class Event(_Common):
    _id = 'event'
    def __init__(self):
        pass

    def get_profiling_info(self, param):
        info = _ffi.new('generic_info *')
        _handle_error(_lib.event__get_profiling_info(self.ptr, param, info))
        return _generic_info_to_python(info)

    def wait(self):
        _handle_error(_lib.event__wait(self.ptr))

def enqueue_nd_range_kernel(queue, kernel, global_work_size, local_work_size, global_work_offset=None, wait_for=None, g_times_l=False):
    if wait_for is not None:
        raise NotImplementedError("wait_for")
    work_dim = len(global_work_size)

    if local_work_size is not None:
        if g_times_l:
            work_dim = max(work_dim, len(local_work_size))
        elif work_dim != len(local_work_size):
            raise RuntimeError("enqueue_nd_range_kernel", status_code.INVALID_VALUE,
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
    _handle_error(_lib._enqueue_nd_range_kernel(
        ptr_event,
        queue.ptr,
        kernel.ptr,
        work_dim,
        c_global_work_offset,
        c_global_work_size,
        c_local_work_size
    ))
    return _create_instance(Event, ptr_event[0])

def _c_obj_list(objs=None):
    if objs is None:
        return _ffi.NULL, 0
    return _ffi.new('void *[]', [ev.ptr for ev in objs]), len(objs)

def _enqueue_read_buffer(queue, mem, buf, device_offset=0, wait_for=None, is_blocking=True):
    c_buf, size = Buffer._c_buffer_from_obj(buf)
    ptr_event = _ffi.new('void **')
    c_wait_for, num_wait_for = _c_obj_list(wait_for)
    _handle_error(_lib._enqueue_read_buffer(
        ptr_event,
        queue.ptr,
        mem.ptr,
        c_buf,
        size,
        device_offset,
        c_wait_for, num_wait_for,
        bool(is_blocking)
    ))
    return _create_instance(Event, ptr_event[0])

def _enqueue_copy_buffer(queue, src, dst, byte_count=-1, src_offset=0, dst_offset=0, wait_for=None):
    ptr_event = _ffi.new('void **')
    c_wait_for, num_wait_for = _c_obj_list(wait_for)
    _handle_error(_lib._enqueue_copy_buffer(
        ptr_event,
        queue.ptr,
        src.ptr,
        dst.ptr,
        byte_count,
        src_offset,
        dst_offset,
        c_wait_for, num_wait_for,
    ))
    return _create_instance(Event, ptr_event[0])

def _enqueue_write_buffer(queue, mem, hostbuf, device_offset=0, wait_for=None, is_blocking=True):
    c_buf, size = Buffer._c_buffer_from_obj(hostbuf)
    ptr_event = _ffi.new('void **')
    c_wait_for, num_wait_for = _c_obj_list(wait_for)
    _handle_error(_lib._enqueue_write_buffer(
        ptr_event,
        queue.ptr,
        mem.ptr,
        c_buf,
        size,
        device_offset,
        c_wait_for, num_wait_for,
        bool(is_blocking)
    ))
    return _create_instance(Event, ptr_event[0])


def _create_instance(cls, ptr):
    ins = cls.__new__(cls)
    ins.ptr = ptr
    return ins

# {{{ gl interop

def have_gl():
    return bool(_lib.have_gl())

class GLBuffer(MemoryObject):
    _id = 'gl_buffer'
    
    def __init__(self, context, flags, bufobj):
        ptr = _ffi.new('void **')
        _handle_error(_lib._create_from_gl_buffer(ptr, context.ptr, flags, bufobj))
        self.ptr = ptr[0]

class GLRenderBuffer(MemoryObject):
    _id = 'gl_renderbuffer'
    
    def __init__(self, context, flags, bufobj):
        ptr = _ffi.new('void **')
        _handle_error(_lib._create_from_gl_renderbuffer(ptr, context.ptr, flags, bufobj))
        self.ptr = ptr[0]

        
def _create_gl_enqueue(what):
    def enqueue_gl_objects(queue, mem_objects, wait_for=None):
        ptr_event = _ffi.new('void **')
        c_wait_for, num_wait_for = _c_obj_list(wait_for)
        c_mem_objects, num_mem_objects = _c_obj_list(mem_objects)
        _handle_error(what(
            ptr_event,
            queue.ptr,
            c_mem_objects,
            num_mem_objects,
            c_wait_for,
            num_wait_for
            ))
        return _create_instance(Event, ptr_event[0])
    return enqueue_gl_objects

enqueue_acquire_gl_objects = _create_gl_enqueue(_lib._enqueue_acquire_gl_objects)
enqueue_release_gl_objects = _create_gl_enqueue(_lib._enqueue_release_gl_objects)

class Image(MemoryObject):
    _id = 'image'

    def __init__(self, context, flags, format, *args):
        if len(args) == 2:
            # > (1,2)
            desc, hostbuf = args
        elif len(args) == 3:
            # <= (1,1)
            shape, pitches, hostbuf = args
        else:
            assert False

# class GLTexture(MemoryObject):
#     _id = 'gl_texture'
    
#     def __init__(self, context, flags, texture_target, miplevel, texture, dims):
#         ptr = _ffi.new('void **')
#         _handle_error(_lib._create_from_gl_texture(ptr, context.ptr, flags, texture_target, miplevel, texture, dims))
#         self.ptr = ptr[0]
