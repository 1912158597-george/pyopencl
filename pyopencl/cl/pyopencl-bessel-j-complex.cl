/*
Evaluate Bessel J function J_v(z) and J_{v+1}(z) with v a nonnegative integer
and z anywhere in the complex plane.

Copyright (C) Vladimir Rokhlin
Copyright (C) 2010-2012 Leslie Greengard and Zydrunas Gimbutas
Copyright (C) 2015 Shidong Jiang, Andreas Kloeckner

/!\ WARNING: GPL-ONLY SOFTWARE

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.  This program is distributed in
the hope that it will be useful, but WITHOUT ANY WARRANTY; without
even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License for more
details. You should have received a copy of the GNU General Public
License along with this program;
if not, see <http://www.gnu.org/licenses/>.

Manually translated from
https://github.com/zgimbutas/fmmlib2d/blob/master/src/cdjseval2d.f

*/

void bessel_j_complex(int v, cdouble_t z, cdouble_t *j_v, cdouble_t *j_vp1)
{
  int n;
  int nmax = 10000;

  int k;
  int kmax=8;

  int vscale, vp1scale;
  double vscaling, vp1scaling;

  const double small = 2e-1;
  const double median = 1.0e0;

  const double upbound = 1e40;
  const double upbound_inv = 1e-40;

  double dd;
  double k_factorial_inv, kv_factorial_inv, kvp1_factorial_inv;

  cdouble_t z_half, mz_half2, mz_half_2k, z_half_v, z_half_vp1;

  cdouble_t ima = {0.0e0, 1.0e0};

  cdouble_t zinv, ztmp;
  cdouble_t j_nm1, j_n, j_np1;

  cdouble_t psi, zsn, zmul, zmulinv;
  cdouble_t unscaled_j_n, unscaled_j_nm1, unscaled_j_np1;
  cdouble_t unscaled_j_v, unscaled_j_vp1;
  cdouble_t scaling;

  // assert( v >= 0 );

#if 0
  if (cdouble_abs(z) < tiny)
  {
    if (v == 0)
    {
      *j_v = (cdouble_t)(1,0);
      *j_vp1 = 0;
    } else
    {
      *j_v = 0;
      *j_vp1 = 0;
    }
    return;
  }
#endif

  // {{{ power series for (small z) or (large v and median z)
  if ( (cdouble_abs(z) < small) || ( (v>12) && (cdouble_abs(z) < median)))
  {
    z_half = cdouble_divider(z,2.0);

    mz_half2 = (-1)*cdouble_mul(z_half,z_half);

    z_half_v = cdouble_powr(z_half, v);
    z_half_vp1 = cdouble_mul(z_half_v, z_half);


    // compute 1/v!
    kv_factorial_inv = 1.0;
    for ( k = 1; k <= v; k++)
    {
      kv_factorial_inv /= k;
    }

    kvp1_factorial_inv = kv_factorial_inv / (v+1);

    k_factorial_inv = 1.0;

    // compute the power series of bessel j function
    mz_half_2k = (cdouble_t)(1.0,0);

    *j_v = 0;
    *j_vp1 = 0;

    for ( k = 0; k < kmax; k++ )
    {
      *j_v = *j_v + cdouble_mulr(mz_half_2k, kv_factorial_inv*k_factorial_inv);
      *j_vp1 = *j_vp1 + cdouble_mulr(mz_half_2k, kvp1_factorial_inv*k_factorial_inv);

      mz_half_2k = cdouble_mul(mz_half_2k, mz_half2);
      k_factorial_inv /= (k+1);
      kv_factorial_inv /= (k+v+1);
      kvp1_factorial_inv /= (k+v+2);
    }

    *j_v = cdouble_mul(*j_v, z_half_v );
    *j_vp1 = cdouble_mul(*j_vp1, z_half_vp1 );

    return;
  }

  // }}}

  // {{{ use recurrence for large z

  j_nm1 = 0;
  j_n = 1;

  n = v;

  zinv = cdouble_rdivide(1,z);

  while (true)
  {
    j_np1 = cdouble_mul((2*n*zinv),j_n) - j_nm1;

    n += 1;
    j_nm1 = j_n;
    j_n = j_np1;

    if (n > nmax)
    {
      *j_v = nan(0x8e55e1u);
      *j_vp1 = nan(0x8e55e1u);
      return;
    }

    dd = pow((cdouble_real(j_n)), 2)+pow(cdouble_imag(j_n),2);
    if (dd > upbound)
      break;
  }

  // downward recursion, account for rescalings
  // Record the number of times of the missed rescalings
  // for j_v and j_vp1.


  unscaled_j_np1 = 0;
  unscaled_j_n = 1;

  // Use normalization condition http://dlmf.nist.gov/10.12#E5
  psi = 0;

  if (cdouble_imag(z) <= 0)
  {
    zmul = ima;
  } else
  {
    zmul = (-1)*ima;
  }

  zsn = cdouble_powr(zmul, n%4);

  zmulinv = cdouble_rdivide(1, zmul);

  vscale = 0;
  vp1scale = 0;

  while (n > 0)
  {
    ztmp = cdouble_mul(2*n*zinv, unscaled_j_n) - unscaled_j_np1;
    dd = pow(cdouble_real(ztmp), 2) + pow(cdouble_imag(ztmp), 2);

    unscaled_j_nm1 = ztmp;


    psi = psi + cdouble_mul(unscaled_j_n, zsn);
    zsn = cdouble_mul(zsn, zmulinv);

    n -= 1;
    unscaled_j_np1 = unscaled_j_n;
    unscaled_j_n = unscaled_j_nm1;

    if (dd > upbound)
    {
      unscaled_j_np1 = cdouble_rmul(upbound_inv, unscaled_j_np1);
      unscaled_j_n = cdouble_rmul(upbound_inv, unscaled_j_n);
      psi = cdouble_rmul(upbound_inv,psi);
      if (n < v) vscale++;
      if (n < v+1) vp1scale++;
    }

    if (n == v)
      unscaled_j_v = unscaled_j_n;
    if (n == v+1)
      unscaled_j_vp1 = unscaled_j_n;

  }

  psi = 2*psi + unscaled_j_n;

  if ( cdouble_imag(z) <= 0 )
  {
    scaling = cdouble_divide( cdouble_exp( cdouble_mul(ima,z) ), psi);
  } else
  {
    scaling = cdouble_divide( cdouble_exp( cdouble_mul(-1*ima,z) ), psi);
  }
  vscaling = pow(upbound_inv, vscale);
  vp1scaling = pow(upbound_inv, vp1scale);

  *j_v = cdouble_mul(unscaled_j_v, cdouble_mulr(scaling, vscaling));
  *j_vp1 = cdouble_mul(unscaled_j_vp1, cdouble_mulr(scaling,vp1scaling));

  // }}}
}

// vim: fdm=marker
