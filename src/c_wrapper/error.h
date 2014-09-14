#include "wrap_cl.h"
#include "pyhelper.h"
#include "clobj.h"
#include "debug.h"

#include <string.h>
#include <stdexcept>
#include <iostream>
#include <utility>
#include <functional>
#include <atomic>

#ifndef __PYOPENCL_ERROR_H
#define __PYOPENCL_ERROR_H

namespace pyopencl {

// {{{ error

class clerror : public std::runtime_error {
private:
    const char *m_routine;
    cl_int m_code;

public:
    clerror(const char *rout, cl_int c, const char *msg="")
        : std::runtime_error(msg), m_routine(rout), m_code(c)
    {
        std::cout << rout <<";" << msg<< ";" << c << std::endl;
    }
    PYOPENCL_INLINE const char*
    routine() const
    {
        return m_routine;
    }

    PYOPENCL_INLINE cl_int
    code() const
    {
        return m_code;
    }

    PYOPENCL_INLINE bool
    is_out_of_memory() const
    {
        return (code() == CL_MEM_OBJECT_ALLOCATION_FAILURE ||
                code() == CL_OUT_OF_RESOURCES ||
                code() == CL_OUT_OF_HOST_MEMORY);
    }
};

// }}}

// {{{ tracing and error reporting

template<typename>
struct __CLArgGetter {
    template<typename T>
    static PYOPENCL_INLINE auto
    get(T&& clarg) -> decltype(clarg.convert())
    {
        return clarg.convert();
    }
};

template<typename T, class = void>
struct __CLFinish {
    static PYOPENCL_INLINE void
    call(T, bool)
    {
    }
};

template<typename T>
struct __CLFinish<T, decltype((void)(std::declval<T>().finish(true)))> {
    static PYOPENCL_INLINE void
    call(T v, bool converted)
    {
        v.finish(converted);
    }
};

template<typename T, class = void>
struct __CLPost {
    static PYOPENCL_INLINE void
    call(T)
    {
    }
};

template<typename T>
struct __CLPost<T, decltype((void)(std::declval<T>().post()))> {
    static PYOPENCL_INLINE void
    call(T v)
    {
        v.post();
    }
};

template<typename T, class = void>
struct __CLPrintOut {
    static PYOPENCL_INLINE void
    call(T, std::ostream&)
    {
    }
};

template<typename T>
struct __CLPrintOut<T, typename std::enable_if<
                           std::remove_reference<T>::type::is_out>::type> {
    static inline void
    call(T v, std::ostream &stm)
    {
        v.print(stm, true);
        stm << ", ";
    }
};

template<typename T, class = void>
struct __CLPrint {
    static inline void
    call(T v, std::ostream &stm)
    {
        v.print(stm);
        stm << ", ";
    }
};

template<template<typename...> class Caller, size_t n, typename T>
struct __CLCall {
    template<typename... Ts>
    static PYOPENCL_INLINE void
    call(T &&t, Ts&&... ts)
    {
        __CLCall<Caller, n - 1, T>::call(std::forward<T>(t),
                                         std::forward<Ts>(ts)...);
        Caller<decltype(std::get<n>(t))>::call(std::get<n>(t),
                                               std::forward<Ts>(ts)...);
    }
};

template<template<typename...> class Caller, typename T>
struct __CLCall<Caller, 0, T> {
    template<typename... Ts>
    static PYOPENCL_INLINE void
    call(T &&t, Ts&&... ts)
    {
        Caller<decltype(std::get<0>(t))>::call(std::get<0>(t),
                                               std::forward<Ts>(ts)...);
    }
};

template<typename... Types>
class CLArgPack : public ArgPack<CLArg, Types...> {
public:
    using ArgPack<CLArg, Types...>::ArgPack;
    template<typename Func>
    PYOPENCL_INLINE auto
    clcall(Func func, const char *name)
        -> decltype(this->template call<__CLArgGetter>(func))
    {
        auto res = this->template call<__CLArgGetter>(func);
        if (DEBUG_ON) {
            typename CLArgPack::tuple_base *that = this;
            std::cerr << name << "(";
            __CLCall<__CLPrint, sizeof...(Types) - 1,
                     decltype(*that)>::call(*that, std::cerr);
            std::cerr << ") = (" << res << ", ";
            __CLCall<__CLPrintOut, sizeof...(Types) - 1,
                     decltype(*that)>::call(*that, std::cerr);
            std::cerr << ")" << std::endl;
        }
        return res;
    }
    PYOPENCL_INLINE void
    finish()
    {
        typename CLArgPack::tuple_base *that = this;
        __CLCall<__CLFinish, sizeof...(Types) - 1,
                 decltype(*that)>::call(*that, false);
        __CLCall<__CLPost, sizeof...(Types) - 1,
                 decltype(*that)>::call(*that);
        __CLCall<__CLFinish, sizeof...(Types) - 1,
                 decltype(*that)>::call(*that, true);
    }
};

template<typename... Types>
static PYOPENCL_INLINE CLArgPack<typename std::remove_reference<Types>::type...>
make_clargpack(Types&&... args)
{
    return CLArgPack<typename std::remove_reference<Types>::type...>(
        std::forward<Types>(args)...);
}

template<typename... ArgTypes2, typename... ArgTypes>
static PYOPENCL_INLINE void
call_guarded(cl_int (*func)(ArgTypes...), const char *name, ArgTypes2&&... args)
{
    auto argpack = make_clargpack(std::forward<ArgTypes2>(args)...);
    cl_int status_code = argpack.clcall(func, name);
    if (status_code != CL_SUCCESS) {
        throw clerror(name, status_code);
    }
    argpack.finish();
}

template<typename T, typename... ArgTypes, typename... ArgTypes2>
PYOPENCL_USE_RESULT static PYOPENCL_INLINE T
call_guarded(T (*func)(ArgTypes...), const char *name, ArgTypes2&&... args)
{
    cl_int status_code = CL_SUCCESS;
    // This magically turns off a weird gcc warning of uninitialized variable.
    auto p = &status_code;
    auto &_p = p;
    auto argpack = make_clargpack(std::forward<ArgTypes2>(args)..., _p);
    T res = argpack.clcall(func, name);
    if (status_code != CL_SUCCESS) {
        throw clerror(name, status_code);
    }
    argpack.finish();
    return res;
}
#define pyopencl_call_guarded(func, args...)    \
    pyopencl::call_guarded(func, #func, args)

template<typename... ArgTypes, typename... ArgTypes2>
static PYOPENCL_INLINE void
call_guarded_cleanup(cl_int (*func)(ArgTypes...), const char *name,
                     ArgTypes2&&... args)
{
    auto argpack = make_clargpack(std::forward<ArgTypes2>(args)...);
    cl_int status_code = argpack.clcall(func, name);
    if (status_code != CL_SUCCESS) {
        std::cerr
            << ("PyOpenCL WARNING: a clean-up operation failed "
                "(dead context maybe?)") << std::endl
            << name << " failed with code " << status_code << std::endl;
    } else {
        argpack.finish();
    }
}
#define pyopencl_call_guarded_cleanup(func, args...)    \
    pyopencl::call_guarded_cleanup(func, #func, args)

PYOPENCL_USE_RESULT static PYOPENCL_INLINE ::error*
c_handle_error(std::function<void()> func) noexcept
{
    try {
        func();
        return nullptr;
    } catch (const clerror &e) {
        auto err = (::error*)malloc(sizeof(::error));
        err->routine = strdup(e.routine());
        err->msg = strdup(e.what());
        err->code = e.code();
        err->other = 0;
        return err;
    } catch (const std::exception &e) {
        /* non-pyopencl exceptions need to be converted as well */
        auto err = (::error*)malloc(sizeof(::error));
        err->other = 1;
        err->msg = strdup(e.what());
        return err;
    }
}

template<typename Func>
static PYOPENCL_INLINE auto
retry_mem_error(Func func) -> decltype(func())
{
    try {
        return func();
    } catch (clerror &e) {
        if (PYOPENCL_LIKELY(!e.is_out_of_memory()) || !py::gc()) {
            throw;
        }
    }
    return func();
}

// }}}

}

#endif
