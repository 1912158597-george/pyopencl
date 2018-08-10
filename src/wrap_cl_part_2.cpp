#include "wrap_cl.hpp"




namespace pyopencl {
#if PYOPENCL_CL_VERSION >= 0x1020
  py::object image_desc_dummy_getter(cl_image_desc &desc)
  {
    return py::none();
  }

  void image_desc_set_shape(cl_image_desc &desc, py::object py_shape)
  {
    COPY_PY_REGION_TRIPLE(shape);
    desc.image_width = shape[0];
    desc.image_height = shape[1];
    desc.image_depth = shape[2];
    desc.image_array_size = shape[2];
  }

  void image_desc_set_pitches(cl_image_desc &desc, py::object py_pitches)
  {
    COPY_PY_PITCH_TUPLE(pitches);
    desc.image_row_pitch = pitches[0];
    desc.image_slice_pitch = pitches[1];
  }

  void image_desc_set_buffer(cl_image_desc &desc, memory_object *mobj)
  {
    if (mobj)
      desc.buffer = mobj->data();
    else
      desc.buffer = 0;
  }

#endif
}




using namespace pyopencl;




void pyopencl_expose_part_2(py::module &m)
{
  // {{{ image

#if PYOPENCL_CL_VERSION >= 0x1020
  {
    typedef cl_image_desc cls;
    py::class_<cls>(m, "ImageDescriptor")
      .def_readwrite("image_type", &cls::image_type)
      .def_property("shape", &image_desc_dummy_getter, image_desc_set_shape)
      .def_readwrite("array_size", &cls::image_array_size)
      .def_property("pitches", &image_desc_dummy_getter, image_desc_set_pitches)
      .def_readwrite("num_mip_levels", &cls::num_mip_levels)
      .def_readwrite("num_samples", &cls::num_samples)
      .def_property("buffer", &image_desc_dummy_getter, image_desc_set_buffer)
      ;
  }
#endif

  {
    typedef image cls;
    py::class_<cls, memory_object>(m, "Image", py::dynamic_attr())
      .def(
          py::init(
            [](
              context const &ctx,
              cl_mem_flags flags,
              cl_image_format const &fmt,
              py::sequence shape,
              py::sequence pitches,
              py::object buffer)
            {
              return create_image(ctx, flags, fmt, shape, pitches, buffer);
            }),
          py::arg("context"),
          py::arg("flags"),
          py::arg("format"),
          py::arg("shape")=py::none(),
          py::arg("pitches")=py::none(),
          py::arg("hostbuf")=py::none()
          )
#if PYOPENCL_CL_VERSION >= 0x1020
      .def(
          py::init(
            [](
              context const &ctx,
              cl_mem_flags flags,
              cl_image_format const &fmt,
              cl_image_desc &desc,
              py::object buffer)
            {
              return create_image_from_desc(ctx, flags, fmt, desc, buffer);
            }),
          py::arg("context"),
          py::arg("flags"),
          py::arg("format"),
          py::arg("desc"),
          py::arg("hostbuf")=py::none()
          )
#endif
      .DEF_SIMPLE_METHOD(get_image_info)
      ;
  }

  {
    typedef cl_image_format cls;
    py::class_<cls>(m, "ImageFormat")
      .def(
          py::init(
            [](cl_channel_order ord, cl_channel_type tp)
            {
              return make_image_format(ord, tp);
            }))
      .def_readwrite("channel_order", &cls::image_channel_order)
      .def_readwrite("channel_data_type", &cls::image_channel_data_type)
      .def_property_readonly("channel_count", &get_image_format_channel_count)
      .def_property_readonly("dtype_size", &get_image_format_channel_dtype_size)
      .def_property_readonly("itemsize", &get_image_format_item_size)
      ;
  }

  DEF_SIMPLE_FUNCTION(get_supported_image_formats);

  m.def("_enqueue_read_image", enqueue_read_image,
      py::arg("queue"),
      py::arg("mem"),
      py::arg("origin"),
      py::arg("region"),
      py::arg("hostbuf"),
      py::arg("row_pitch")=0,
      py::arg("slice_pitch")=0,
      py::arg("wait_for")=py::none(),
      py::arg("is_blocking")=true
      );
  m.def("_enqueue_write_image", enqueue_write_image,
      py::arg("queue"),
      py::arg("mem"),
      py::arg("origin"),
      py::arg("region"),
      py::arg("hostbuf"),
      py::arg("row_pitch")=0,
      py::arg("slice_pitch")=0,
      py::arg("wait_for")=py::none(),
      py::arg("is_blocking")=true
      );

  m.def("_enqueue_copy_image", enqueue_copy_image,
      py::arg("queue"),
      py::arg("src"),
      py::arg("dest"),
      py::arg("src_origin"),
      py::arg("dest_origin"),
      py::arg("region"),
      py::arg("wait_for")=py::none()
      );
  m.def("_enqueue_copy_image_to_buffer", enqueue_copy_image_to_buffer,
      py::arg("queue"),
      py::arg("src"),
      py::arg("dest"),
      py::arg("origin"),
      py::arg("region"),
      py::arg("offset"),
      py::arg("wait_for")=py::none()
      );
  m.def("_enqueue_copy_buffer_to_image", enqueue_copy_buffer_to_image,
      py::arg("queue"),
      py::arg("src"),
      py::arg("dest"),
      py::arg("offset"),
      py::arg("origin"),
      py::arg("region"),
      py::arg("wait_for")=py::none()
      );

#if PYOPENCL_CL_VERSION >= 0x1020
  m.def("enqueue_fill_image", enqueue_fill_image,
      py::arg("queue"),
      py::arg("mem"),
      py::arg("color"),
      py::arg("origin"),
      py::arg("region"),
      py::arg("wait_for")=py::none()
      );
#endif

  // }}}

  // {{{ memory_map
  {
    typedef memory_map cls;
    py::class_<cls>(m, "MemoryMap", py::dynamic_attr())
      .def("release", &cls::release,
          py::arg("queue")=0,
          py::arg("wait_for")=py::none()
          )
      ;
  }

  m.def("enqueue_map_buffer", enqueue_map_buffer,
      py::arg("queue"),
      py::arg("buf"),
      py::arg("flags"),
      py::arg("offset"),
      py::arg("shape"),
      py::arg("dtype"),
      py::arg("order")="C",
      py::arg("strides")=py::none(),
      py::arg("wait_for")=py::none(),
      py::arg("is_blocking")=true);
  m.def("enqueue_map_image", enqueue_map_image,
      py::arg("queue"),
      py::arg("img"),
      py::arg("flags"),
      py::arg("origin"),
      py::arg("region"),
      py::arg("shape"),
      py::arg("dtype"),
      py::arg("order")="C",
      py::arg("strides")=py::none(),
      py::arg("wait_for")=py::none(),
      py::arg("is_blocking")=true);

  // }}}

  // {{{ sampler
  {
    typedef sampler cls;
    py::class_<cls>(m, "Sampler", py::dynamic_attr())
      .def(py::init<context const &, bool, cl_addressing_mode, cl_filter_mode>())
      .DEF_SIMPLE_METHOD(get_info)
      .def(py::self == py::self)
      .def(py::self != py::self)
      .def("__hash__", &cls::hash)
      PYOPENCL_EXPOSE_TO_FROM_INT_PTR(cl_sampler)
      ;
  }

  // }}}

  // {{{ program
  {
    typedef program cls;
    py::enum_<cls::program_kind_type>(m, "program_kind")
      .value("UNKNOWN", cls::KND_UNKNOWN)
      .value("SOURCE", cls::KND_SOURCE)
      .value("BINARY", cls::KND_BINARY)
      ;

    py::class_<cls>(m, "_Program", py::dynamic_attr())
      .def(
          py::init(
            [](context &ctx, std::string const &src)
            {
              return create_program_with_source(ctx, src);
            }),
          py::arg("context"),
          py::arg("src"))
      .def(
          py::init(
            [](context &ctx, py::sequence devices, py::sequence binaries)
            {
              return create_program_with_binary(ctx, devices, binaries);
            }),
          py::arg("context"),
          py::arg("devices"),
          py::arg("binaries"))
#if (PYOPENCL_CL_VERSION >= 0x1020) && \
      ((PYOPENCL_CL_VERSION >= 0x1030) && defined(__APPLE__))
      .def_static("create_with_built_in_kernels",
          create_program_with_built_in_kernels,
          py::arg("context"),
          py::arg("devices"),
          py::arg("kernel_names"),
          py::return_value_policy<py::manage_new_object>())
#endif
      .DEF_SIMPLE_METHOD(kind)
      .DEF_SIMPLE_METHOD(get_info)
      .DEF_SIMPLE_METHOD(get_build_info)
      .def("_build", &cls::build,
          py::arg("options")="",
          py::arg("devices")=py::none())
#if PYOPENCL_CL_VERSION >= 0x1020
      .def("compile", &cls::compile,
          py::arg("options")="",
          py::arg("devices")=py::none(),
          py::arg("headers")=py::list())
      .def_static("link", &link_program,
          py::arg("context"),
          py::arg("programs"),
          py::arg("options")="",
          py::arg("devices")=py::none()
          )
#endif
      .def(py::self == py::self)
      .def(py::self != py::self)
      .def("__hash__", &cls::hash)
      .def("all_kernels", create_kernels_in_program)
      PYOPENCL_EXPOSE_TO_FROM_INT_PTR(cl_program)
      ;
  }

#if PYOPENCL_CL_VERSION >= 0x1020
  m.def("unload_platform_compiler", unload_platform_compiler);
#endif

  // }}}

  // {{{ kernel

  {
    typedef kernel cls;
    py::class_<cls>(m, "Kernel", py::dynamic_attr())
      .def(py::init<const program &, std::string const &>())
      .DEF_SIMPLE_METHOD(get_info)
      .DEF_SIMPLE_METHOD(get_work_group_info)
      .def("_set_arg_null", &cls::set_arg_null)
      .def("_set_arg_buf", &cls::set_arg_buf)
      .DEF_SIMPLE_METHOD(set_arg)
#if PYOPENCL_CL_VERSION >= 0x1020
      .DEF_SIMPLE_METHOD(get_arg_info)
#endif
      .def(py::self == py::self)
      .def(py::self != py::self)
      .def("__hash__", &cls::hash)
      PYOPENCL_EXPOSE_TO_FROM_INT_PTR(cl_kernel)
      ;
  }

  {
    typedef local_memory cls;
    py::class_<cls>(m, "LocalMemory", py::dynamic_attr())
      .def(
          py::init<size_t>(),
          py::arg("size"))
      .def_property_readonly("size", &cls::size)
      ;
  }


  m.def("enqueue_nd_range_kernel", enqueue_nd_range_kernel,
      py::arg("queue"),
      py::arg("kernel"),
      py::arg("global_work_size"),
      py::arg("local_work_size"),
      py::arg("global_work_offset")=py::none(),
      py::arg("wait_for")=py::none(),
      py::arg("g_times_l")=false
      );
  m.def("enqueue_task", enqueue_task,
      py::arg("queue"),
      py::arg("kernel"),
      py::arg("wait_for")=py::none()
      );

  // TODO: clEnqueueNativeKernel
  // }}}

  // {{{ GL interop
  DEF_SIMPLE_FUNCTION(have_gl);

#ifdef HAVE_GL

#ifdef __APPLE__
  DEF_SIMPLE_FUNCTION(get_apple_cgl_share_group);
#endif /* __APPLE__ */

  {
    typedef gl_buffer cls;
    py::class_<cls, memory_object>(m, "GLBuffer", py::dynamic_attr())
      .def(
          py::init(
            [](context &ctx, cl_mem_flags flags, GLuint bufobj)
            {
              return create_from_gl_buffer(ctx, flags, bufobj);
            }),
          py::arg("context"),
          py::arg("flags"),
          py::arg("bufobj"))
      .def("get_gl_object_info", get_gl_object_info)
      ;
  }

  {
    typedef gl_renderbuffer cls;
    py::class_<cls, memory_object>(m, "GLRenderBuffer", py::dynamic_attr())
      .def(
          py::init(
            [](context &ctx, cl_mem_flags flags, GLuint bufobj)
            {
              return create_from_gl_renderbuffer(ctx, flags, bufobj);
            }),
          py::arg("context"),
          py::arg("flags"),
          py::arg("bufobj"))
      .def("get_gl_object_info", get_gl_object_info)
      ;
  }

  {
    typedef gl_texture cls;
    py::class_<cls, image>(m, "GLTexture", py::dynamic_attr())
      .def(
          py::init(
            [](context &ctx, cl_mem_flags flags, GLenum texture_target,
              GLint miplevel, GLuint texture, unsigned dims)
            {
              return create_from_gl_texture(ctx, flags, texture_target, miplevel, texture, dims);
            }),
          py::arg("context"),
          py::arg("flags"),
          py::arg("texture_target"),
          py::arg("miplevel"),
          py::arg("texture"),
          py::arg("dims"))
      .def("get_gl_object_info", get_gl_object_info)
      .DEF_SIMPLE_METHOD(get_gl_texture_info)
      ;
  }

  m.def("enqueue_acquire_gl_objects", enqueue_acquire_gl_objects,
      py::arg("queue"),
      py::arg("mem_objects"),
      py::arg("wait_for")=py::none()
      );
  m.def("enqueue_release_gl_objects", enqueue_release_gl_objects,
      py::arg("queue"),
      py::arg("mem_objects"),
      py::arg("wait_for")=py::none()
      );

#if defined(cl_khr_gl_sharing) && (cl_khr_gl_sharing >= 1)
  m.def("get_gl_context_info_khr", get_gl_context_info_khr,
      py::arg("properties"),
      py::arg("param_name"),
      py::arg("platform")=py::none()
      );
#endif

#endif
  // }}}
}


// vim: foldmethod=marker
