from __future__ import division, with_statement, absolute_import, print_function

__copyright__ = """
Copyright (c) 2011, Eric Bainville
Copyright (c) 2015, Ilya Efimoff
All rights reserved.
"""

# based on code at http://www.bealto.com/gpu-sorting_intro.html

__license__ = """
Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
this list of conditions and the following disclaimer in the documentation
and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors
may be used to endorse or promote products derived from this software without
specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import pyopencl as cl
from pyopencl.tools import dtype_to_ctype
from operator import mul
from functools import reduce
from pytools import memoize_method
from mako.template import Template

import pyopencl.bitonic_sort_templates as _tmpl


def _is_power_of_2(n):
    from pyopencl.tools import bitlog2
    return n == 0 or 2**bitlog2(n) == n


class BitonicSort(object):
    """Sort an array (or one axis of one) using a sorting network.

    Will only work if the axis of the array to be sorted has a length
    that is a power of 2.

    .. versionadded:: 2015.2
    """

    kernels_srcs = {
            'B2': _tmpl.ParallelBitonic_B2,
            'B4': _tmpl.ParallelBitonic_B4,
            'B8': _tmpl.ParallelBitonic_B8,
            'B16': _tmpl.ParallelBitonic_B16,
            'C4': _tmpl.ParallelBitonic_C4,
            'BL': _tmpl.ParallelBitonic_Local,
            'BLO': _tmpl.ParallelBitonic_Local_Optim,
            'PML': _tmpl.ParallelMerge_Local
            }

    def __init__(self, context, key_dtype, idx_dtype=None):
        self.dtype = dtype_to_ctype(key_dtype)
        self.context = context
        if idx_dtype is None:
            self.idx_t = 'uint'  # Dummy

        else:
            self.idx_t = dtype_to_ctype(idx_dtype)

    def __call__(self, arr, idx=None, mkcpy=True, queue=None, wait_for=None, axis=0):
        if queue is None:
            queue = arr.queue

        if wait_for is None:
            wait_for = []
        wait_for = wait_for + arr.events

        last_evt = cl.enqueue_marker(queue, wait_for=wait_for)

        if arr.shape[axis] == 0:
            return arr, last_evt

        if not _is_power_of_2(arr.shape[axis]):
            raise ValueError("sorted array axis length must be a power of 2")

        arr = arr.copy() if mkcpy else arr

        if idx is None:
            argsort = 0
        else:
            argsort = 1

        run_queue = self.sort_b_prepare_wl(argsort, arr.shape, axis)
        knl, nt, wg, aux = run_queue[0]

        if idx is not None:
            if aux:
                last_evt = knl(
                        queue, (nt,), wg, arr.data, idx.data,
                        cl.LocalMemory(wg[0]*4*arr.dtype.itemsize),
                        cl.LocalMemory(wg[0]*4*idx.dtype.itemsize),
                        wait_for=[last_evt])
            for knl, nt, wg, _ in run_queue[1:]:
                last_evt = knl(
                        queue, (nt,), wg, arr.data, idx.data,
                        wait_for=[last_evt])

        else:
            if aux:
                last_evt = knl(
                        queue, (nt,), wg, arr.data,
                        cl.LocalMemory(wg[0]*4*arr.dtype.itemsize),
                        wait_for=[last_evt])
            for knl, nt, wg, _ in run_queue[1:]:
                last_evt = knl(queue, (nt,), wg, arr.data, wait_for=[last_evt])

        return arr, last_evt

    @memoize_method
    def get_program(self, letter, argsort, params):
        defstpl = Template(_tmpl.defines)

        defs = defstpl.render(
                NS="\\", argsort=argsort, inc=params[0], dir=params[1],
                dtype=params[2], idxtype=params[3],
                dsize=params[4], nsize=params[5])

        kid = Template(self.kernels_srcs[letter]).render(argsort=argsort)

        prg = cl.Program(self.context, defs + kid).build()
        return prg

    @memoize_method
    def sort_b_prepare_wl(self, argsort, shape, axis):
        run_queue = []
        ds = int(shape[axis])
        size = reduce(mul, shape)
        ndim = len(shape)

        ns = reduce(mul, shape[(axis+1):]) if axis < ndim-1 else 1

        ds = int(shape[axis])
        allowb4 = True
        allowb8 = True
        allowb16 = True

        wg = min(ds, self.context.devices[0].max_work_group_size)
        length = wg >> 1
        prg = self.get_program(
                'BLO', argsort, (1, 1, self.dtype, self.idx_t, ds, ns))
        run_queue.append((prg.run, size, (wg,), True))

        while length < ds:
            inc = length
            while inc > 0:
                ninc = 0
                direction = length << 1
                if allowb16 and inc >= 8 and ninc == 0:
                    letter = 'B16'
                    ninc = 4
                elif allowb8 and inc >= 4 and ninc == 0:
                    letter = 'B8'
                    ninc = 3
                elif allowb4 and inc >= 2 and ninc == 0:
                    letter = 'B4'
                    ninc = 2
                elif inc >= 0:
                    letter = 'B2'
                    ninc = 1

                nthreads = size >> ninc

                prg = self.get_program(letter, argsort,
                        (inc, direction, self.dtype, self.idx_t,  ds, ns))
                run_queue.append((prg.run, nthreads, None, False,))
                inc >>= ninc

            length <<= 1

        return run_queue
