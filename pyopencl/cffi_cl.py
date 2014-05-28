from __future__ import division

__copyright__ = """
Copyright (C) 2013 Marko Bencun
Copyright (C) 2014 Andreas Kloeckner
"""

__license__ = """
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""


import warnings
import numpy as np
import sys

# TODO: can we do without ctypes?
import ctypes

from pyopencl._cffi import _ffi, _lib

# are we running on pypy?
_PYPY = '__pypy__' in sys.builtin_module_names

try:
    _unicode = unicode
except:
    _unicode = str
    _bytes = bytes
else:
    try:
        _bytes = bytes
    except:
        _bytes = str

def _convert_str(s):
    if isinstance(s, _unicode):
        return s.encode()
    return s

# {{{ wrapper tools

# {{{ _CArray helper classes

class _CArray(object):
    def __init__(self, ptr):
        self.ptr = ptr
        self.size = _ffi.new('uint32_t *')

    def __del__(self):
        if self.ptr != _ffi.NULL:
            _lib.pyopencl_free_pointer(self.ptr[0])

    def __getitem__(self, key):
        return self.ptr[0].__getitem__(key)

    def __iter__(self):
        for i in xrange(self.size[0]):
            yield self[i]


class _CArrays(_CArray):
    def __del__(self):
        _lib.pyopencl_free_pointer_array(
                _ffi.cast('void**', self.ptr[0]), self.size[0])
        super(_CArrays, self).__del__()

# }}}


# {{{ GetInfo support

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
            if info.opaque_class == _lib.CLASS_PROGRAM:  # TODO: HACK?
                from . import Program
                return Program(ins)
            return ins

        if type_.endswith(']'):
            ret = map(ci, value)
            _lib.pyopencl_free_pointer(info.value)
            return ret
        else:
            return ci(value)
    if type_ == 'char*':
        ret = _ffi.string(value)
    elif type_.startswith('char*['):
        ret = map(_ffi.string, value)
        _lib.pyopencl_free_pointer_array(info.value, len(value))
    elif type_.endswith(']'):
        if type_.startswith('char['):
            ret = ''.join(a[0] for a in value)
        elif type_.startswith('generic_info['):
            ret = list(map(_generic_info_to_python, value))
        elif type_.startswith('cl_image_format['):
            ret = [
                    ImageFormat(
                        imf.image_channel_order,
                        imf.image_channel_data_type)
                    for imf in value]
        else:
            ret = list(value)
    else:
        ret = value[0]
    if info.dontfree == 0:
        _lib.pyopencl_free_pointer(info.value)
    return ret

# }}}


def _c_obj_list(objs=None):
    if objs is None:
        return _ffi.NULL, 0
    return _ffi.new('void *[]', [ev.ptr for ev in objs]), len(objs)


def _create_instance(cls, ptr):
    ins = cls.__new__(cls)
    ins.ptr = ptr
    return ins


# {{{ common base class

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
        _lib._from_int_ptr(ptr, int_ptr_value,
                getattr(_lib, 'CLASS_%s' % cls._id.upper()))
        #getattr(_lib, '%s__from_int_ptr' % cls._id)(ptr, int_ptr_value)
        return _create_instance(cls, ptr[0])

# }}}

# }}}


def get_cl_header_version():
    v = _lib.pyopencl_get_cl_version()
    return (v >> (3*4),
            (v >> (1*4)) & 0xff)


# {{{ constants

_constants = {}


class _NoInit(object):
    def __init__(self):
        raise RuntimeError("This class cannot be instantiated.")


# {{{ constant classes
# These will be overwritten below and exist to placate pyflakes.

class status_code(_NoInit):
    pass


class context_properties(_NoInit):
    pass


class device_type(_NoInit):
    pass


class mem_flags(_NoInit):
    pass


class mem_object_type(_NoInit):
    pass


class channel_order(_NoInit):
    pass


class channel_type(_NoInit):
    pass

# }}}


@_ffi.callback('void(const char*, const char* name, long value)')
def _constant_callback(type_, name, value):
    s_type = _ffi.string(type_)
    _constants.setdefault(s_type, {})
    _constants[s_type][_ffi.string(name)] = value
_lib.populate_constants(_constant_callback)

for type_, d in _constants.iteritems():
    if sys.version_info >= (3,):
        type_ = type_.decode()
    locals()[type_] = type(type_, (_NoInit,), d)

# }}}


# {{{ exceptions

class Error(Exception):
    def __init__(self, msg='', routine='', code=0):
        self.routine = routine
        assert isinstance(code, int)
        self.code = code
        self.what = msg
        super(Error, self).__init__(msg)


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
        _lib.pyopencl_free_pointer(error.msg)
        _lib.pyopencl_free_pointer(error)
        raise e
    if error.code == status_code.MEM_OBJECT_ALLOCATION_FAILURE:
        klass = MemoryError
    elif error.code <= status_code.INVALID_VALUE:
        klass = LogicError
    elif status_code.INVALID_VALUE < error.code < status_code.SUCCESS:
        klass = RuntimeError
    else:
        klass = Error

    e = klass(routine=_ffi.string(error.routine),
            code=error.code, msg=_ffi.string(error.msg))
    _lib.pyopencl_free_pointer(error.routine)
    _lib.pyopencl_free_pointer(error.msg)
    _lib.pyopencl_free_pointer(error)
    raise e

# }}}


# {{{ Platform

class Platform(_Common):
    _id = 'platform'
    # todo: __del__

    def get_devices(self, device_type=device_type.ALL):
        devices = _CArray(_ffi.new('void**'))
        _handle_error(_lib.platform__get_devices(
            self.ptr, devices.ptr, devices.size, device_type))

        result = []
        for i in xrange(devices.size[0]):
            # TODO why is the cast needed?
            device_ptr = _ffi.cast('void**', devices.ptr[0])[i]
            result.append(_create_instance(Device, device_ptr))
        return result


def get_platforms():
    platforms = _CArray(_ffi.new('void**'))
    _handle_error(_lib.get_platforms(platforms.ptr, platforms.size))
    result = []
    for i in xrange(platforms.size[0]):
        # TODO why is the cast needed?
        platform_ptr = _ffi.cast('void**', platforms.ptr[0])[i]
        result.append(_create_instance(Platform, platform_ptr))

    return result

# }}}


# {{{ Device

class Device(_Common):
    _id = 'device'

    # TODO: __del__

    def get_info(self, param):
        return super(Device, self).get_info(param)

# }}}


# {{{ Context

def _parse_context_properties(properties):
    props = []
    if properties is None:
        return _ffi.NULL

    for prop_tuple in properties:
        if len(prop_tuple) != 2:
            raise RuntimeError("Context", status_code.INVALID_VALUE,
                    "property tuple must have length 2")

        prop, value = prop_tuple
        if prop is None:
            raise RuntimeError("Context", status_code.INVALID_VALUE,
                    "invalid context property")

        props.append(prop)
        if prop == context_properties.PLATFORM:
            props.append(value.int_ptr)

        # TODO: used to be ifdef _WIN32? Why?
        elif prop == getattr(context_properties, "WGL_HDC_KHR"):
            props.append(value)

        elif prop in [getattr(context_properties, key, None) for key in (
                'CONTEXT_PROPERTY_USE_CGL_SHAREGROUP_APPLE',
                'GL_CONTEXT_KHR',
                'EGL_DISPLAY_KHR',
                'GLX_DISPLAY_KHR',
                'CGL_SHAREGROUP_KHR',
                )]:

            val = (ctypes.cast(value, ctypes.c_void_p)).value
            if val is None:
                raise LogicError("Context",
                        status_code.INVALID_VALUE,
                        "You most likely have not initialized OpenGL properly.")
            props.append(val)
        else:
            raise RuntimeError("Context", status_code.INVALID_VALUE,
                    "invalid context property")
    props.append(0)
    return _ffi.new('cl_context_properties[]', props)


class Context(_Common):
    _id = 'context'

    def __init__(self, devices=None, properties=None, dev_type=None):
        c_props = _parse_context_properties(properties)
        status_code = _ffi.new('cl_int *')

        # from device list
        if devices is not None:
            if dev_type is not None:
                raise RuntimeError("Context", status_code.INVALID_VALUE,
                        "one of 'devices' or 'dev_type' must be None")
            ptr_devices = _ffi.new('void*[]', [device.ptr for device in devices])
            ptr_ctx = _ffi.new('void **')
            _handle_error(_lib._create_context(
                ptr_ctx, c_props, len(ptr_devices),
                _ffi.cast('void**', ptr_devices)))

        else:  # TODO: from dev_type
            raise NotImplementedError()

        self.ptr = ptr_ctx[0]

# }}}


# {{{ CommandQueue

class CommandQueue(_Common):
    _id = 'command_queue'

    def __init__(self, context, device=None, properties=None):
        if properties is None:
            properties = 0

        ptr_command_queue = _ffi.new('void **')

        _handle_error(_lib._create_command_queue(
            ptr_command_queue, context.ptr,
            _ffi.NULL if device is None else device.ptr, properties))

        self.ptr = ptr_command_queue[0]
    def finish(self):
        _handle_error(_lib._command_queue_finish(self.ptr))
    def flush(self):
        _handle_error(_lib._command_queue_flush(self.ptr))

class MemoryObjectHolder(_Common):
    pass


class MemoryObject(MemoryObjectHolder):
    def release(self):
        _handle_error(_lib._release_memobj(self.ptr))

def _c_buffer_from_obj(obj, writable=False):
    """Convert a Python object to a tuple (cdata('void *'), num_bytes, dummy)
    to be able to pass a data stream to a C function. The dummy variable exists
    only to ensure that the Python object referencing the C buffer is not
    garbage collected at the end of this function, making the C buffer itself
    invalid.
    """

    if _PYPY:
        # {{{ special case: numpy (also works with numpypy)

        if isinstance(obj, np.ndarray):
            # numpy array
            return (
                    _ffi.cast('void *',
                        obj.__array_interface__['data'][0]),
                    obj.nbytes,
                    None)
        elif isinstance(obj, np.generic):
            # numpy scalar
            #
            # * obj.__array_interface__ exists in CPython, but the address does
            #   not seem to point to the actual scalar (not supported/bug?).
            #
            # * does not exist (yet?) in numpypy.

            s_array = np.array([obj])  # obj[()] not supported yet by numpypy
            return (
                    _ffi.cast('void *',
                        s_array.__array_interface__['data'][0]),
                    s_array.nbytes,
                    s_array)
        elif isinstance(obj, bytes):
            if writable:
                # There sould be better ways to pass arguments
                p = _ffi.new('char[]', obj)
                return (_ffi.cast('void *', p), len(obj), p)
            return (obj, len(obj), None)
        else:
            raise LogicError("", status_code.INVALID_VALUE,
                    "PyOpencl on PyPy only accepts numpy arrays "
                    "and scalars arguments")

        # }}}

    # TODO: is there a cross-interpreter solution?

    # {{{ fall back to the old CPython buffer protocol API

    addr = ctypes.c_void_p()
    length = ctypes.c_ssize_t()

    try:
        if writable:
            status = ctypes.pythonapi.PyObject_AsWriteBuffer(
                    ctypes.py_object(obj), ctypes.byref(addr), ctypes.byref(length))
        else:
            status = ctypes.pythonapi.PyObject_AsReadBuffer(
                    ctypes.py_object(obj), ctypes.byref(addr), ctypes.byref(length))
    except TypeError:
        raise LogicError("", status_code.INVALID_VALUE,
                "PyOpencl does not accept bare Python types as arguments")
    else:
        if status:
            raise Exception('TODO error_already_set')
    return _ffi.cast('void *', addr.value), length.value, None

    # }}}

# }}}


# {{{ Buffer

class Buffer(MemoryObject):
    _id = 'buffer'

    def __init__(self, context, flags, size=0, hostbuf=None):
        if hostbuf is not None and not (
                flags & (mem_flags.USE_HOST_PTR | mem_flags.COPY_HOST_PTR)):
            warnings.warn("'hostbuf' was passed, but no memory flags "
                    "to make use of it.")

        c_hostbuf = _ffi.NULL
        if hostbuf is not None:
            c_hostbuf, hostbuf_size, _ = _c_buffer_from_obj(
                    hostbuf, writable=flags & mem_flags.USE_HOST_PTR)
            if size > hostbuf_size:
                raise RuntimeError("Buffer", status_code.INVALID_VALUE,
                        "Specified size is greater than host buffer size")
            if size == 0:
                size = hostbuf_size

        ptr_buffer = _ffi.new('void **')
        _handle_error(_lib._create_buffer(
            ptr_buffer, context.ptr, flags, size, c_hostbuf))
        self.ptr = ptr_buffer[0]

# }}}


# {{{ Program

class _Program(_Common):
    _id = 'program'

    def __init__(self, *args):
        if len(args) == 2:
            self._init_source(*args)
        else:
            self._init_binary(*args)

    def _init_source(self, context, src):
        ptr_program = _ffi.new('void **')
        _handle_error(_lib._create_program_with_source(
            ptr_program, context.ptr, _convert_str(src)))
        self.ptr = ptr_program[0]

    def _init_binary(self, context, devices, binaries):
        if len(devices) != len(binaries):
            raise RuntimeError("create_program_with_binary",
                    status_code.INVALID_VALUE,
                    "device and binary counts don't match")

        ptr_program = _ffi.new('void **')
        ptr_devices = _ffi.new('void*[]', [device.ptr for device in devices])
        ptr_binaries = [_ffi.new('char[%i]' % len(binary), binary)
                for binary in binaries]
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

        _handle_error(
                _lib.program__build(self.ptr,
                    _convert_str(options), num_devices,
                    _ffi.cast('void**', ptr_devices)))

    def get_build_info(self, device, param):
        info = _ffi.new('generic_info *')
        _handle_error(_lib.program__get_build_info(
            self.ptr, device.ptr, param, info))
        return _generic_info_to_python(info)

# }}}


# {{{ Kernel

class Kernel(_Common):
    _id = 'kernel'

    def __init__(self, program, name):
        ptr_kernel = _ffi.new('void **')
        _handle_error(_lib._create_kernel(ptr_kernel, program.ptr,
                                          _convert_str(name)))
        self.ptr = ptr_kernel[0]

    def set_arg(self, arg_index, arg):
        if arg is None:
            _handle_error(_lib.kernel__set_arg_null(self.ptr, arg_index))
        elif isinstance(arg, MemoryObjectHolder):
            _handle_error(_lib.kernel__set_arg_mem(self.ptr, arg_index, arg.ptr))
        elif isinstance(arg, Sampler):
            _handle_error(_lib.kernel__set_arg_sampler(self.ptr, arg_index, arg.ptr))
        else:
            # todo: how to handle args other than numpy arrays?
            c_buf, size, _ = _c_buffer_from_obj(arg)
            _handle_error(_lib.kernel__set_arg_buf(self.ptr, arg_index, c_buf, size))

    def get_work_group_info(self, param, device):
        info = _ffi.new('generic_info *')
        _handle_error(_lib.kernel__get_work_group_info(
            self.ptr, param, device.ptr, info))
        return _generic_info_to_python(info)

# }}}


# {{{ Event

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

# }}}


# {{{ enqueue_nd_range_kernel

def enqueue_nd_range_kernel(queue, kernel,
        global_work_size, local_work_size, global_work_offset=None,
        wait_for=None, g_times_l=False):

    work_dim = len(global_work_size)

    if local_work_size is not None:
        global_size_copied = False
        if g_times_l:
            work_dim = max(work_dim, len(local_work_size))
        elif work_dim != len(local_work_size):
            raise RuntimeError("enqueue_nd_range_kernel",
                               status_code.INVALID_VALUE,
                               "global/local work sizes have differing dimensions")

        if len(local_work_size) < work_dim:
            local_work_size = (local_work_size +
                               [1] * (work_dim - len(local_work_size)))
        if len(global_work_size) < work_dim:
            global_size_copied = True
            global_work_size = (global_work_size +
                                [1] * (work_dim - len(global_work_size)))
        if g_times_l:
            if not global_size_copied:
                global_work_size = list(global_work_size)
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
    c_wait_for, num_wait_for = _c_obj_list(wait_for)
    _handle_error(_lib._enqueue_nd_range_kernel(
        ptr_event,
        queue.ptr,
        kernel.ptr,
        work_dim,
        c_global_work_offset,
        c_global_work_size,
        c_local_work_size,
        c_wait_for, num_wait_for
    ))
    return _create_instance(Event, ptr_event[0])

# }}}

# {{{ _enqueue_marker_*

def _enqueue_marker_with_wait_list(queue, wait_for=None):
    ptr_event = _ffi.new('void **')
    c_wait_for, num_wait_for = _c_obj_list(wait_for)
    _handle_error(_lib._enqueue_marker_with_wait_list(
        ptr_event,
        queue.ptr,
        c_wait_for, num_wait_for))
    return _create_instance(Event, ptr_event[0])

def _enqueue_marker(queue):
    ptr_event = _ffi.new('void **')
    _handle_error(_lib._enqueue_marker(ptr_event, queue.ptr))
    return _create_instance(Event, ptr_event[0])

# }}}

# {{{ _enqueue_barrier_*

def _enqueue_barrier_with_wait_list(queue, wait_for=None):
    ptr_event = _ffi.new('void **')
    c_wait_for, num_wait_for = _c_obj_list(wait_for)
    _handle_error(_lib._enqueue_barrier_with_wait_list(
        ptr_event,
        queue.ptr,
        c_wait_for, num_wait_for))
    return _create_instance(Event, ptr_event[0])

def _enqueue_barrier(queue):
    _handle_error(_lib._enqueue_barrier(queue.ptr))

# }}}

# {{{ _enqueue_*_buffer

def _enqueue_read_buffer(queue, mem, hostbuf, device_offset=0,
                         wait_for=None, is_blocking=True):
    c_buf, size, _ = _c_buffer_from_obj(hostbuf, writable=True)
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


def _enqueue_copy_buffer(queue, src, dst, byte_count=-1, src_offset=0,
        dst_offset=0, wait_for=None):
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


def _enqueue_write_buffer(queue, mem, hostbuf, device_offset=0,
        wait_for=None, is_blocking=True):
    c_buf, size, _ = _c_buffer_from_obj(hostbuf)
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

# }}}


# {{{ _enqueue_*_image

def _enqueue_read_image(queue, mem, origin, region,
        hostbuf, row_pitch=0, slice_pitch=0, wait_for=None, is_blocking=True):
    c_buf, size, _ = _c_buffer_from_obj(hostbuf, writable=True)
    ptr_event = _ffi.new('void **')
    c_wait_for, num_wait_for = _c_obj_list(wait_for)
    _handle_error(_lib._enqueue_read_image(
        ptr_event,
        queue.ptr,
        mem.ptr,
        origin,
        region,
        c_buf,
        size,
        row_pitch, slice_pitch,
        c_wait_for, num_wait_for,
        bool(is_blocking)
    ))
    return _create_instance(Event, ptr_event[0])

# TODO: write_image? copy_image?...

# }}}


# {{{ gl interop

def have_gl():
    return bool(_lib.pyopencl_have_gl())


class GLBuffer(MemoryObject):
    _id = 'gl_buffer'

    def __init__(self, context, flags, bufobj):
        ptr = _ffi.new('void **')
        _handle_error(_lib._create_from_gl_buffer(
            ptr, context.ptr, flags, bufobj))
        self.ptr = ptr[0]


class GLRenderBuffer(MemoryObject):
    _id = 'gl_renderbuffer'

    def __init__(self, context, flags, bufobj):
        ptr = _ffi.new('void **')
        _handle_error(_lib._create_from_gl_renderbuffer(
            ptr, context.ptr, flags, bufobj))
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

if _lib.pyopencl_have_gl():
    enqueue_acquire_gl_objects = _create_gl_enqueue(_lib._enqueue_acquire_gl_objects)
    enqueue_release_gl_objects = _create_gl_enqueue(_lib._enqueue_release_gl_objects)

# }}}


# {{{ ImageFormat

class ImageFormat(object):
    def __new__(cls, channel_order=0, channel_type=0):
        args = [channel_order, channel_type]
        cls = type(cls.__name__, (cls,), {})

        cls.channel_order = property(
                lambda self: args[0],
                lambda self, v: args.__setitem__(0, v))
        cls.channel_data_type = property(
                lambda self: args[1],
                lambda self, v: args.__setitem__(1, v))

        return object.__new__(cls)

    @property
    def channel_count(self):
        try:
            return {
                channel_order.R: 1,
                channel_order.A: 1,
                channel_order.RG: 2,
                channel_order.RA: 2,
                channel_order.RGB: 3,
                channel_order.RGBA: 4,
                channel_order.BGRA: 4,
                channel_order.INTENSITY: 1,
                channel_order.LUMINANCE: 1,
            }[self.channel_order]
        except KeyError:
            raise LogicError("ImageFormat.channel_count",
                             status_code.INVALID_VALUE,
                             "unrecognized channel order")

    @property
    def dtype_size(self):
        try:
            return {
                channel_type.SNORM_INT8: 1,
                channel_type.SNORM_INT16: 2,
                channel_type.UNORM_INT8: 1,
                channel_type.UNORM_INT16: 2,
                channel_type.UNORM_SHORT_565: 2,
                channel_type.UNORM_SHORT_555: 2,
                channel_type.UNORM_INT_101010: 4,
                channel_type.SIGNED_INT8: 1,
                channel_type.SIGNED_INT16: 2,
                channel_type.SIGNED_INT32: 4,
                channel_type.UNSIGNED_INT8: 1,
                channel_type.UNSIGNED_INT16: 2,
                channel_type.UNSIGNED_INT32: 4,
                channel_type.HALF_FLOAT: 2,
                channel_type.FLOAT: 4,
            }[self.channel_data_type]
        except KeyError:
            raise LogicError("ImageFormat.channel_dtype_size",
                             status_code.INVALID_VALUE,
                             "unrecognized channel data type")

    @property
    def itemsize(self):
        return self.channel_count * self.dtype_size

    def __repr__(self):
        return "ImageFormat(%s, %s)" % (
                channel_order.to_string(self.channel_order,
                    "<unknown channel order 0x%x>"),
                channel_type.to_string(self.channel_data_type,
                    "<unknown channel data type 0x%x>"))

    def __eq__(self, other):
        return (self.channel_order == other.channel_order
                and self.channel_data_type == other.channel_data_type)

    def __ne__(self, other):
        return not self.__eq__(self, other)

    def __hash__(self):
        return hash((ImageFormat, self.channel_order, self.channel_data_type))


def get_supported_image_formats(context, flags, image_type):
    info = _ffi.new('generic_info *')
    _handle_error(_lib._get_supported_image_formats(
        context.ptr, flags, image_type, info))
    return _generic_info_to_python(info)

# }}}


# {{{ Image

class Image(MemoryObject):
    _id = 'image'

    def __init__(self, *args):
        if len(args) == 5:
            # > (1,2)
            context, flags, format, desc, hostbuf = args
        elif len(args) == 6:
            # legacy init for CL 1.1 and older
            self._init_legacy(*args)

        else:
            assert False

    def _init_legacy(self, context, flags, format, shape, pitches, buffer):
        if shape is None:
            raise LogicError("Image", status_code.INVALID_VALUE,
                    "'shape' must be given")

        if buffer is None:
            c_buf, size = _ffi.NULL, 0
        else:
            c_buf, size, _ = _c_buffer_from_obj(
                    buffer, writable=flags & mem_flags.USE_HOST_PTR)

        dims = len(shape)
        if dims == 2:
            width, height = shape
            pitch = 0
            if pitches is not None:
                try:
                    pitch, = pitches
                except ValueError:
                    raise LogicError("Image", status_code.INVALID_VALUE,
                            "invalid length of pitch tuple")

            # check buffer size
            if (buffer is not None
                    and max(pitch, width*format.itemsize)*height > size):
                raise LogicError("Image", status_code.INVALID_VALUE,
                        "buffer too small")

            ptr = _ffi.new('void **')
            _handle_error(_lib._create_image_2d(
                ptr,
                context.ptr,
                flags,
                _ffi.new('struct _cl_image_format *',
                    (format.channel_order, format.channel_data_type, )),
                width, height, pitch,
                c_buf,
                size))
            self.ptr = ptr[0]
        elif dims == 3:
            width, height, depth = shape
            pitch_x, pitch_y = 0, 0
            if pitches is not None:
                try:
                    pitch_x, pitch_y = pitches
                except ValueError:
                    raise LogicError("Image", status_code.INVALID_VALUE,
                            "invalid length of pitch tuple")

            # check buffer size
            if (buffer is not None
                    and (
                        max(
                            max(
                                pitch_x,
                                width*format.itemsize)*height,
                            pitch_y
                            ) * depth > size)):
                raise LogicError("Image", status_code.INVALID_VALUE,
                    "buffer too small")

            ptr = _ffi.new('void **')
            _handle_error(_lib._create_image_3d(
                ptr,
                context.ptr,
                flags,
                _ffi.new('struct _cl_image_format *',
                    (format.channel_order, format.channel_data_type, )),
                width, height, depth, pitch_x, pitch_y,
                c_buf,
                size))

            self.ptr = ptr[0]
        else:
            raise LogicError("Image", status_code.INVALID_VALUE,
                    "invalid dimension")

    def get_image_info(self, param):
        info = _ffi.new('generic_info *')
        _handle_error(_lib.image__get_image_info(self.ptr, param, info))
        return _generic_info_to_python(info)

    @property
    def shape(self):
        if self.type == mem_object_type.IMAGE2D:
            return (self.width, self.height)
        elif self.type == mem_object_type.IMAGE3D:
            return (self.width, self.height, self.depth)
        else:
            raise LogicError("Image", status_code.INVALID_VALUE,
                    "only images have shapes")

# }}}


# {{{ Sampler

class Sampler(_Common):
    _id = 'sampler'

    def __init__(self, context, normalized_coords, addressing_mode, filter_mode):
        ptr = _ffi.new('void **')
        _handle_error(_lib._create_sampler(
            ptr,
            context.ptr,
            normalized_coords,
            addressing_mode,
            filter_mode))
        self.ptr = ptr[0]

# }}}


# {{{ GLTexture (TODO)

class GLTexture(Image):
    _id = 'gl_texture'

    def __init__(self, context, flags, texture_target, miplevel, texture, dims):
        raise NotImplementedError("GLTexture")

        ptr = _ffi.new('void **')
        _handle_error(_lib._create_from_gl_texture(
            ptr, context.ptr, flags, texture_target, miplevel, texture, dims))
        self.ptr = ptr[0]

# }}}

# vim: foldmethod=marker
