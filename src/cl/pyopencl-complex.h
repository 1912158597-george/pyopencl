/*
 * Copyright (c) 1999
 * Silicon Graphics Computer Systems, Inc.
 *
 * Copyright (c) 1999
 * Boris Fomitchev
 *
 * Copyright (c) 2012
 * Andreas Kloeckner
 *
 * This material is provided "as is", with absolutely no warranty expressed
 * or implied. Any use is at your own risk.
 *
 * Permission to use or copy this software for any purpose is hereby granted
 * without fee, provided the above notices are retained on all copies.
 * Permission to modify the code and to distribute modified code is granted,
 * provided the above notices are retained, and a notice that the code was
 * modified is included with the above copyright notice.
 *
 */

// This file is available for inclusion in pyopencl kernels and provides
// complex types 'cfloat_t' and 'cdouble_t', along with a number of special
// functions as visible below, e.g. cdouble_log(z).
//
// Under the hood, the complex types are simply float2 and double2.
// Note that addition (real + complex) and multiplication (complex*complex)
// are defined, but yield wrong results.

#define PYOPENCL_DECLARE_COMPLEX_TYPE_INT(REAL_TP, REAL_3LTR, TPROOT, TP) \
  \
  REAL_TP TPROOT##_real(TP a) { return a.x; } \
  REAL_TP TPROOT##_imag(TP a) { return a.y; } \
  REAL_TP TPROOT##_abs(TP a) { return hypot(a.x, a.y); } \
  \
  TP TPROOT##_fromreal(REAL_TP a) { return (TP)(a, 0); } \
  TP TPROOT##_conj(TP a) { return (TP)(a.x, -a.y); } \
  \
  TP TPROOT##_mul(TP a, TP b) \
  { \
    return (TP)( \
        a.x*b.x - a.y*b.y, \
        a.x*b.y + a.y*b.x); \
  } \
  \
  TP TPROOT##_rdivide(REAL_TP z1, TP z2) \
  { \
    REAL_TP ar = z2.x >= 0 ? z2.x : -z2.x; \
    REAL_TP ai = z2.y >= 0 ? z2.y : -z2.y; \
    \
    if (ar <= ai) { \
      REAL_TP ratio = z2.x / z2.y; \
      REAL_TP denom = z2.y * (1 + ratio * ratio); \
      return (TP)((z1 * ratio) / denom, - z1 / denom); \
    } \
    else { \
      REAL_TP ratio = z2.y / z2.x; \
      REAL_TP denom = z2.x * (1 + ratio * ratio); \
      return (TP)(z1 / denom, - (z1 * ratio) / denom); \
    } \
  } \
  \
  TP TPROOT##_divide(TP z1, TP z2) \
  { \
    REAL_TP ar = z2.x >= 0 ? z2.x : -z2.x; \
    REAL_TP ai = z2.y >= 0 ? z2.y : -z2.y; \
    \
    if (ar <= ai) { \
      REAL_TP ratio = z2.x / z2.y; \
      REAL_TP denom = z2.y * (1 + ratio * ratio); \
      return (TP)( \
         (z1.x * ratio + z1.y) / denom, \
         (z1.y * ratio - z1.x) / denom); \
    } \
    else { \
      REAL_TP ratio = z2.y / z2.x; \
      REAL_TP denom = z2.x * (1 + ratio * ratio); \
      return (TP)( \
         (z1.x + z1.y * ratio) / denom, \
         (z1.y - z1.x * ratio) / denom); \
    } \
  } \
  \
  TP TPROOT##_pow(TP a, TP b) \
  { \
    REAL_TP logr = log(hypot(a.x, a.y)); \
    REAL_TP logi = atan2(a.y, a.x); \
    REAL_TP x = exp(logr * b.x - logi * b.y); \
    REAL_TP y = logr * b.y + logi * b.x; \
    \
    REAL_TP cosy; \
    REAL_TP siny = sincos(y, &cosy); \
    return (TP) (x*cosy, x*siny); \
  } \
  \
  TP TPROOT##_powr(TP a, REAL_TP b) \
  { \
    REAL_TP logr = log(hypot(a.x, a.y)); \
    REAL_TP logi = atan2(a.y, a.x); \
    REAL_TP x = exp(logr * b); \
    REAL_TP y = logi * b; \
    \
    REAL_TP cosy; \
    REAL_TP siny = sincos(y, &cosy); \
    \
    return (TP)(x * cosy, x*siny); \
  } \
  \
  TP TPROOT##_rpow(REAL_TP a, TP b) \
  { \
    REAL_TP logr = log(a); \
    REAL_TP x = exp(logr * b.x); \
    REAL_TP y = logr * b.y; \
    \
    REAL_TP cosy; \
    REAL_TP siny = sincos(y, &cosy); \
    return (TP) (x * cosy, x * siny); \
  } \
  \
  TP TPROOT##_sqrt(TP a) \
  { \
    REAL_TP re = a.x; \
    REAL_TP im = a.y; \
    REAL_TP mag = hypot(re, im); \
    TP result; \
    \
    if (mag == 0.f) { \
      result.x = result.y = 0.f; \
    } else if (re > 0.f) { \
      result.x = sqrt(0.5f * (mag + re)); \
      result.y = im/result.x/2.f; \
    } else { \
      result.y = sqrt(0.5f * (mag - re)); \
      if (im < 0.f) \
        result.y = - result.y; \
      result.x = im/result.y/2.f; \
    } \
    return result; \
  } \
  \
  TP TPROOT##_exp(TP a) \
  { \
    REAL_TP expr = exp(a.x); \
    REAL_TP cosi; \
    REAL_TP sini = sincos(a.y, &cosi); \
    return (TP)(expr * cosi, expr * sini); \
  } \
  \
  TP TPROOT##_log(TP a) \
  { return (TP)(log(hypot(a.x, a.y)), atan2(a.y, a.x)); } \
  \
  TP TPROOT##_sin(TP a) \
  { \
    REAL_TP cosr; \
    REAL_TP sinr = sincos(a.x, &cosr); \
    return (TP)(sinr*cosh(a.y), cosr*sinh(a.y)); \
  } \
  \
  TP TPROOT##_cos(TP a) \
  { \
    REAL_TP cosr; \
    REAL_TP sinr = sincos(a.x, &cosr); \
    return (TP)(cosr*cosh(a.y), -sinr*sinh(a.y)); \
  } \
  \
  TP TPROOT##_tan(TP a) \
  { \
    REAL_TP re2 = 2.f * a.x; \
    REAL_TP im2 = 2.f * a.y; \
    \
    const REAL_TP limit = log(REAL_3LTR##_MAX); \
    \
    if (fabs(im2) > limit) \
      return (TP)(0.f, (im2 > 0 ? 1.f : -1.f)); \
    else \
    { \
      REAL_TP den = cos(re2) + cosh(im2); \
      return (TP) (sin(re2) / den, sinh(im2) / den); \
    } \
  } \
  \
  TP TPROOT##_sinh(TP a) \
  { \
    REAL_TP cosi; \
    REAL_TP sini = sincos(a.y, &cosi); \
    return (TP)(sinh(a.x)*cosi, cosh(a.x)*sini); \
  } \
  \
  TP TPROOT##_cosh(TP a) \
  { \
    REAL_TP cosi; \
    REAL_TP sini = sincos(a.y, &cosi); \
    return (TP)(cosh(a.x)*cosi, sinh(a.x)*sini); \
  } \
  \
  TP TPROOT##_tanh(TP a) \
  { \
    REAL_TP re2 = 2.f * a.x; \
    REAL_TP im2 = 2.f * a.y; \
    \
    const REAL_TP limit = log(REAL_3LTR##_MAX); \
    \
    if (fabs(re2) > limit) \
      return (TP)((re2 > 0 ? 1.f : -1.f), 0.f); \
    else \
    { \
      REAL_TP den = cosh(re2) + cos(im2); \
      return (TP) (sinh(re2) / den, sin(im2) / den); \
    } \
  } \

#define PYOPENCL_DECLARE_COMPLEX_TYPE(BASE, BASE_3LTR) \
  typedef BASE##2 c##BASE##_t; \
  \
  PYOPENCL_DECLARE_COMPLEX_TYPE_INT(BASE, BASE_3LTR, c##BASE, c##BASE##_t)

PYOPENCL_DECLARE_COMPLEX_TYPE(float, FLT);
#define cfloat_cast(a) ((cfloat_t) ((a).x, (a).y))

#ifdef DBL_EPSILON
PYOPENCL_DECLARE_COMPLEX_TYPE(double, DBL);
#define cdouble_cast(a) ((cdouble_t) ((a).x, (a).y))
#endif
