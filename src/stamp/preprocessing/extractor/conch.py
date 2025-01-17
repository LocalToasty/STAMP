import torch

from stamp.preprocessing.extractor import Extractor

try:
    from conch.open_clip_custom import create_model_from_pretrained
except ModuleNotFoundError as e:
    raise ModuleNotFoundError(
        "conch dependencies not installed."
        " Please reinstall stamp using `pip install 'stamp[conch]'`"
    ) from e


class StampConchModel(torch.nn.Module):
    def __init__(self, model) -> None:
        super().__init__()
        self.model = model

    def forward(self, batch: torch.Tensor) -> torch.Tensor:
        return self.model.encode_image(batch, proj_contrast=False, normalize=False)


def conch() -> Extractor:
    model, preprocess = create_model_from_pretrained(  # type: ignore
        "conch_ViT-B-16", "hf_hub:MahmoodLab/conch"
    )

    return Extractor(
        model=StampConchModel(model),
        transform=preprocess,
        identifier="mahmood-conch",  # type: ignore
    )
