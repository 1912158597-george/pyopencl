from __future__ import division

import pyopencl as cl

class CLCharacterizationWarning(UserWarning):
    pass

def has_double_support(dev):
    for ext in dev.extensions.split(" "):
        if ext == "cl_khr_fp64":
            return True
    return False




def has_amd_double_support(dev):
    """"Fix to allow incomplete amd double support in low end boards"""

    for ext in dev.extensions.split(" "):
        if ext == "cl_amd_fp64":
            return True
    return False




def reasonable_work_group_size_multiple(dev, ctx=None):
    try:
        return dev.warp_size_nv
    except AttributeError:
        pass

    if ctx is None:
        ctx = cl.Context([dev])
    prg = cl.Program(ctx, """
        void knl(float *a)
        {
            a[get_global_id(0)] = 0;
        }
        """)
    return prg.knl.get_work_group_info(
            cl.kernel_work_group_info.PREFERRED_WORK_GROUP_SIZE_MULTIPLE,
            dev)




def nv_compute_capability(dev):
    try:
        return (dev.compute_capability_major_nv,
                dev.compute_capability_minor_nv)
    except:
        return None




def usable_local_mem_size(dev, nargs=None):
    """Return an estimate of the usable local memory size.
    :arg nargs: Number of 32-bit arguments passed.
    """
    usable_local_mem_size = dev.local_mem_size

    nv_compute_cap = nv_compute_capability(dev)

    if (nv_compute_cap is not None
            and nv_compute_cap < (2,0)):
        # pre-Fermi use local mem for parameter passing
        if nargs is None:
            # assume maximum
            usable_local_mem_size -= 256
        else:
            usable_local_mem_size -= 4*nargs

    return usable_local_mem_size




def simultaneous_work_items_on_local_access(dev):
    """Return the number of work items that access local
    memory simultaneously and thereby may conflict with
    each other.
    """
    nv_compute_cap = nv_compute_capability(dev)

    if nv_compute_cap is not None:
        if nv_compute_cap < (2,0):
            return 16
        else:
            if nv_compute_cap >= (3,0):
                from warnings import warn
                warn("wildly guessing conflicting local access size on '%s'"
                        % dev,
                        CLCharacterizationWarning)

            return 32

    if dev.type == cl.device_type.GPU:
        from warnings import warn
        warn("wildly guessing conflicting local access size on '%s'"
                % dev,
                CLCharacterizationWarning)
        return 16
    elif dev.type == cl.device_type.CPU:
        return 1
    else:
        from warnings import warn
        warn("wildly guessing conflicting local access size on '%s'"
                % dev,
                CLCharacterizationWarning)
        return 16





def local_memory_access_granularity(dev):
    """Return the number of bytes per bank in local memory."""
    return 4




def local_memory_bank_count(dev):
    """Return the number of banks present in local memory.
    """
    nv_compute_cap = nv_compute_capability(dev)

    if nv_compute_cap is not None:
        if nv_compute_cap < (2,0):
            return 16
        else:
            if nv_compute_cap >= (3,0):
                from warnings import warn
                warn("wildly guessing conflicting local access size on '%s'"
                        % dev,
                        CLCharacterizationWarning)

            return 32

    if dev.type == cl.device_type.GPU:
        from warnings import warn
        warn("wildly guessing conflicting local access size on '%s'"
                % dev,
                CLCharacterizationWarning)
        return 16
    elif dev.type == cl.device_type.CPU:
        return dev.local_mem_size / local_memory_access_granularity(dev)
    else:
        from warnings import warn
        warn("wildly guessing conflicting local access size on '%s'"
                % dev,
                CLCharacterizationWarning)
        return 16



def why_not_local_access_conflict_free(dev, itemsize,
        array_shape, array_stored_shape=None):
    """
    :param itemsize: size of accessed data in bytes
    :param array_shape: array dimensions, fastest-moving last
        (C order)
    """
    # FIXME: Treat 64-bit access on NV CC 2.x + correctly

    if array_stored_shape is None:
        array_stored_shape = array_shape

    rank = len(array_shape)

    array_shape = array_shape[::-1]
    array_stored_shape = array_stored_shape[::-1]

    gran = local_memory_access_granularity(dev)
    if itemsize != gran:
        from warnings import warn
        print gran
        warn("local conflict info might be inaccurate "
                "for itemsize != %d" % gran,
                CLCharacterizationWarning)

    sim_wi = simultaneous_work_items_on_local_access(dev)
    bank_count = local_memory_bank_count(dev)

    conflicts = []

    for work_item_axis in range(rank):

        bank_accesses = {}
        for work_item_id in xrange(sim_wi):
            addr = 0
            addr_mult = itemsize

            idx = []
            left_over_idx = work_item_id
            for axis, (ax_size, ax_stor_size) in enumerate(
                    zip(array_shape, array_stored_shape)):

                if axis >= work_item_axis:
                    left_over_idx, ax_idx = divmod(left_over_idx, ax_size)
                    addr += addr_mult*ax_idx
                    idx.append(ax_idx)
                else:
                    idx.append(0)

                addr_mult *= ax_stor_size

            if left_over_idx:
                # out-of-bounds, assume not taking place
                continue

            bank = (addr // gran) % bank_count
            bank_accesses.setdefault(bank, []).append(
                    "w.item %s -> %s" % (work_item_id, idx[::-1]))

        conflict_multiplicity = max(
                len(acc) for acc in bank_accesses.itervalues())

        if conflict_multiplicity > 1:
            for bank, acc in bank_accesses.iteritems():
                if len(acc) == conflict_multiplicity:
                    conflicts.append(
                            (conflict_multiplicity,
                                "%dx conflict on axis %d (from right, 0-based): "
                                "%s access bank %d" % (
                                    conflict_multiplicity,
                                    work_item_axis,
                                    ", ".join(acc), bank)))

    if conflicts:
        return max(conflicts)
    else:
        return 1, None
