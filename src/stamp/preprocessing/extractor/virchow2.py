import os
from pathlib import Path

import timm
import torch
from timm.data import resolve_data_config
from timm.data.transforms_factory import create_transform
from timm.layers import SwiGLUPacked

from stamp.preprocessing.extractor import Extractor

_stamp_cache_dir = (
    Path(os.environ.get("XDG_CACHE_HOME") or (Path.home() / ".cache")) / "stamp"
)


class Virchow2clsOnly(torch.nn.Module):
    def __init__(self, model) -> None:
        super().__init__()
        self.model = model

    def forward(self, batch: torch.Tensor) -> torch.Tensor:
        return self.model(batch)[:,0]


def virchow2():
    """Extracts features from slide tiles using Virchow2 tile encoder."""

    #checkpoint_path = Path(_stamp_cache_dir) / "virchow2" / "pytorch_model.bin"

    # Load the model structure
    model = timm.create_model(
        "hf-hub:paige-ai/Virchow2",
        pretrained=True,
        mlp_layer=SwiGLUPacked,
        act_layer=torch.nn.SiLU,
    )

    # Load the state dict from the checkpoint file
    #model.load_state_dict(torch.load(checkpoint_path))

    # Define the transform
    transform = create_transform(
        **resolve_data_config(model.pretrained_cfg, model=model)
    )

    return Extractor(
        model=Virchow2clsOnly(model),
        transform=transform,
        identifier="virchow2",  # type: ignore
    )
