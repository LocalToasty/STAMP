import os
from pathlib import Path

import timm
from timm.models.vision_transformer import VisionTransformer
import torch
from torchvision import transforms
from stamp.preprocessing.extractor import Extractor


def dinoSSL():
    """Extracts features from slide tiles using DinoSSLPath tile encoder."""

    model = VisionTransformer(
        img_size=224, patch_size=16, embed_dim=384, num_heads=6, num_classes=0
    )
    pretrained_url = "https://github.com/lunit-io/benchmark-ssl-pathology/releases/download/pretrained-weights/dino_vit_small_patch16_ep200.torch"

    # Download and save the state_dict without loading into a model
    state_dict = torch.hub.load_state_dict_from_url(pretrained_url, map_location='cpu', progress=True)
    model.load_state_dict(state_dict)

    LUNIT_MEAN = (0.70322989, 0.53606487, 0.66096631)
    LUNIT_STD = (0.21716536, 0.26081574, 0.20723464)

    transform = transforms.Compose([
        transforms.Resize(224),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=LUNIT_MEAN, std=LUNIT_STD)
    ])
    
    return Extractor(
        model=model,
        transform=transform,
        identifier="dinoSSL",  # type: ignore
    )