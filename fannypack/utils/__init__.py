from ..data import _trajectories_file
from ._buddy import Buddy
from ._conversions import to_device, to_numpy, to_torch
from ._deprecation import deprecation_wrapper, new_name_wrapper
from ._git import get_git_commit_hash
from ._module_freezing import freeze_module, unfreeze_module
from ._pdb_safety_net import pdb_safety_net
from ._psd_helpers import (
    gaussian_log_prob,
    matrix_dim_from_tril_count,
    quadratic_matmul,
    tril_count_from_matrix_dim,
    tril_to_vector,
    vector_to_tril,
)
from ._slice_wrapper import SliceWrapper
from ._squeeze import squeeze

DictIterator = new_name_wrapper(
    "fannypack.utils.DictIterator", "fannypack.utils.SliceWrapper", SliceWrapper,
)

TrajectoriesFile = new_name_wrapper(
    "fannypack.utils.TrajectoriesFiles",
    "fannypack.data.TrajectoriesFile",
    _trajectories_file.TrajectoriesFile,
)
