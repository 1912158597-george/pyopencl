#include "error.h"

#ifndef __PYOPENCL_PLATFORM_H
#define __PYOPENCL_PLATFORM_H

namespace pyopencl {

// {{{ platform

class platform : public clobj<cl_platform_id> {
public:
    using clobj::clobj;
    PYOPENCL_DEF_CL_CLASS(PLATFORM);

    generic_info get_info(cl_uint param_name) const;
};

// }}}

}

#endif
