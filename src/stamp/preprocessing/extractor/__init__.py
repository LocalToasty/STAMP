from collections.abc import Callable
from dataclasses import KW_ONLY, dataclass

import torch
from PIL import Image
from torch import nn

__author__ = "Marko van Treeck"
__copyright__ = "Copyright (C) 2022-2024 Marko van Treeck"
__license__ = "MIT"


@dataclass(frozen=True)
class Extractor:
    _: KW_ONLY
    model: nn.Module
    transform: Callable[[Image.Image], torch.Tensor]
    identifier: str
    """An ID _uniquely_ identifying the model and extractor.
    
    If possible, it should include the digest of the model weights etc.
    so that any change in the model also changes its ID.
    """
