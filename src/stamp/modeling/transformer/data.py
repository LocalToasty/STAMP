"""Helper classes to manage pytorch data."""

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import h5py
import numpy as np
import numpy.typing as npt
import pandas as pd
import torch
from torch.utils.data import Dataset

__all__ = ["BagDataset", "make_dataset", "get_cohort_df"]

__author__ = "Marko van Treeck"
__copyright__ = "Copyright (C) 2022-2024 Marko van Treeck"
__license__ = "MIT"


class MapDataset(Dataset):
    def __init__(
        self, func: Callable, *datasets: Sequence, strict: bool = True
    ) -> None:
        """A dataset mapping over a function over other datasets.

        Args:
            func:  Function to apply to the underlying datasets.  Has to accept
                `len(dataset)` arguments.
            datasets:  The datasets to map over.
            strict:  Enforce the datasets to have the same length.  If
                false, then all datasets will be truncated to the shortest
                dataset's length.
        """
        if strict:
            assert all(
                len(ds) == len(datasets[0])  # pyright: ignore[reportArgumentType]
                for ds in datasets
            ), "datasets have differing lengths"
            self._len = len(datasets[0])  # pyright: ignore[reportArgumentType]
        elif datasets:
            self._len = min(
                len(ds)
                for ds in datasets  # pyright: ignore[reportArgumentType]
            )
        else:
            self._len = 0

        self._datasets = datasets
        self.func = func

    def __len__(self) -> int:
        return self._len

    def __getitem__(self, index: int) -> Any:
        return self.func(*[ds[index] for ds in self._datasets])

    def new_empty(self):
        # FIXME hack to appease fastai's export
        return self


class SKLearnEncoder(Protocol):
    """An sklearn-style encoder."""

    categories_: Sequence[Sequence[str]]

    def transform(self, x: npt.NDArray): ...


class EncodedDataset(MapDataset):
    def __init__(self, encode: SKLearnEncoder, values: Sequence) -> None:
        """A dataset which first encodes its input data.

        This class is can be useful with classes such as fastai, where the
        encoder is saved as part of the model.

        Args:
            encode:  an sklearn encoding to encode the data with.
            values:  data to encode.
        """
        super().__init__(self._unsqueeze_to_float32, values)
        self.encode = encode

    def _unsqueeze_to_float32(self, x):
        return torch.tensor(
            self.encode.transform(np.array(x).reshape(1, -1)), dtype=torch.float32
        )


@dataclass
class BagDataset(Dataset):
    """A dataset of bags of instances."""

    bags: Sequence[Iterable[Path]]
    """The `.h5` files containing the bags.

    Each bag consists of the features taken from one or multiple h5 files.
    Each of the h5 files needs to have a dataset called `feats` of shape N x
    F, where N is the number of instances and F the number of features per
    instance.
    """
    bag_size: int | None = None
    """The number of instances in each bag.

    For bags containing more instances, a random sample of `bag_size`
    instances will be drawn.  Smaller bags are padded with zeros.  If
    `bag_size` is None, all the samples will be used.
    """

    def __len__(self):
        return len(self.bags)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, int]:
        # collect all the features
        feats = []
        for bag_file in self.bags[index]:
            with h5py.File(bag_file, "r") as f:
                feats.append(
                    torch.from_numpy(f["feats"][:])  # pyright: ignore[reportIndexIssue]
                )
        feats = torch.concat(feats).float()

        # sample a subset, if required
        if self.bag_size:
            return _to_fixed_size_bag(feats, bag_size=self.bag_size)
        else:
            return feats, len(feats)


def _to_fixed_size_bag(
    bag: torch.Tensor, bag_size: int = 512
) -> tuple[torch.Tensor, int]:
    # get up to bag_size elements
    bag_idxs = torch.randperm(bag.shape[0])[:bag_size]
    bag_samples = bag[bag_idxs]

    # zero-pad if we don't have enough samples
    zero_padded = torch.cat(
        (
            bag_samples,
            torch.zeros(bag_size - bag_samples.shape[0], bag_samples.shape[1]),
        )
    )
    return zero_padded, min(bag_size, len(bag))


def make_dataset(
    *,
    bags: Sequence[Iterable[Path]],
    targets: tuple[SKLearnEncoder, Sequence[Any]],
    add_features: Iterable[tuple[Any, Sequence[Any]]] | None = None,
    bag_size: int | None = None,
) -> MapDataset:
    if add_features:
        return _make_multi_input_dataset(
            bags=bags, targets=targets, add_features=add_features, bag_size=bag_size
        )
    else:
        return _make_basic_dataset(
            bags=bags, target_enc=targets[0], targs=targets[1], bag_size=bag_size
        )


def get_target_enc(mil_learn):
    return mil_learn.dls.train.dataset._datasets[-1].encode


def _make_basic_dataset(
    *,
    bags: Sequence[Iterable[Path]],
    target_enc: SKLearnEncoder,
    targs: Sequence[Any],
    bag_size: int | None = None,
) -> MapDataset:
    assert len(bags) == len(targs), "number of bags and ground truths does not match!"

    ds = MapDataset(
        zip_bag_targ,
        BagDataset(bags, bag_size=bag_size),  # pyright: ignore[reportArgumentType]
        EncodedDataset(target_enc, targs),  # pyright: ignore[reportArgumentType]
    )

    return ds


def zip_bag_targ(bag, targets):
    features, lengths = bag
    return (
        features,
        lengths,
        targets.squeeze(),
    )


def _make_multi_input_dataset(
    *,
    bags: Sequence[Iterable[Path]],
    targets: tuple[SKLearnEncoder, Sequence[Any]],
    add_features: Iterable[tuple[Any, Sequence[Any]]],
    bag_size: int | None = None,
) -> MapDataset:
    target_enc, targs = targets
    assert len(bags) == len(targs), "number of bags and ground truths does not match!"
    for i, (_, vals) in enumerate(add_features):
        assert len(vals) == len(
            targs
        ), f"number of additional attributes #{i} and ground truths does not match!"

    bag_ds = BagDataset(bags, bag_size=bag_size)

    add_ds = MapDataset(
        _splat_concat,
        *[
            EncodedDataset(enc, vals)  # pyright: ignore[reportArgumentType]
            for enc, vals in add_features
        ],
    )

    targ_ds = EncodedDataset(target_enc, targs)

    ds = MapDataset(
        _attach_add_to_bag_and_zip_with_targ,
        bag_ds,  # pyright: ignore[reportArgumentType]
        add_ds,  # pyright: ignore[reportArgumentType]
        targ_ds,  # pyright: ignore[reportArgumentType]
    )

    return ds


def _splat_concat(*x):
    return torch.concat(x, dim=1)


def _attach_add_to_bag_and_zip_with_targ(bag, add, targ):
    return (
        torch.concat(
            [
                bag[0],  # the bag's features
                add.repeat(bag[0].shape[0], 1),  # the additional features
            ],
            dim=1,
        ),
        bag[1],  # the bag's length
        targ.squeeze(),  # the ground truth
    )


def get_cohort_df(
    clini_table: Path,
    slide_table: Path,
    feature_dir: Path,
    target_label: str,
    categories: Iterable[str],
) -> pd.DataFrame:
    clini_df = (
        pd.read_csv(clini_table, dtype=str)
        if Path(clini_table).suffix == ".csv"
        else pd.read_excel(clini_table, dtype=str)
    )
    slide_df = (
        pd.read_csv(slide_table, dtype=str)
        if Path(slide_table).suffix == ".csv"
        else pd.read_excel(slide_table, dtype=str)
    )

    if "PATIENT" not in clini_df.columns:
        raise ValueError(
            "The PATIENT column is missing in the clini_table.\n\
                         Please ensure the patient identifier column is named PATIENT."
        )

    if "PATIENT" not in slide_df.columns:
        raise ValueError(
            "The PATIENT column is missing in the slide_table.\n\
                         Please ensure the patient identifier column is named PATIENT."
        )

    # Avoid FILENAME_x causing merge conflict
    if "FILENAME" in clini_df.columns and "FILENAME" in slide_df.columns:
        clini_df = clini_df.drop(columns=["FILENAME"])

    df = clini_df.merge(slide_df, on="PATIENT")
    # remove uninteresting
    df = df[df[target_label].isin(categories)]  # pyright: ignore[reportArgumentType]
    # remove slides we don't have
    h5s = set(feature_dir.glob("*.h5"))
    assert h5s, f"no features found in {feature_dir}!"
    h5_df = pd.DataFrame(
        h5s,
        columns=["slide_path"],  # pyright: ignore[reportArgumentType]
    )
    h5_df["FILENAME"] = h5_df.slide_path.map(lambda p: p.stem)
    df = df.merge(h5_df, on="FILENAME")

    # reduce to one row per patient with list of slides in `df['slide_path']`
    patient_df = df.groupby("PATIENT").first().drop(columns="slide_path")
    patient_slides = df.groupby("PATIENT").slide_path.apply(list)
    df = patient_df.merge(
        patient_slides, left_on="PATIENT", right_index=True
    ).reset_index()

    return df
