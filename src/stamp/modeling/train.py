from pathlib import Path
from typing import cast

import lightning
import lightning.pytorch
import lightning.pytorch.accelerators
import lightning.pytorch.accelerators.accelerator
import numpy.typing as npt
from lightning.pytorch.accelerators.accelerator import Accelerator
from lightning.pytorch.callbacks import EarlyStopping, ModelCheckpoint
from lightning.pytorch.loggers import CSVLogger
from sklearn.model_selection import train_test_split

from stamp.modeling.data import (
    BagDataset,
    Category,
    PatientId,
    dataloader_from_patient_data,
    filter_complete_patient_data_,
    patient_to_ground_truth_from_clini_table_,
    slide_to_patient_from_slide_table_,
)
from stamp.modeling.lightning_model import (
    Bags,
    BagSizes,
    EncodedTargets,
    LitVisionTransformer,
)

__all__ = ["train_categorical_model_"]


__author__ = "Marko van Treeck"
__copyright__ = "Copyright (C) 2024 Marko van Treeck"
__license__ = "MIT"


def train_categorical_model_(
    *,
    clini_table: Path,
    slide_table: Path,
    feature_dir: Path,
    output_dir: Path,
    patient_label: str,
    ground_truth_label: str,
    filename_label: str,
    categories: npt.NDArray[Category] | None,
    # Dataset and -loader parameters
    bag_size: int,
    num_workers: int,
    # Training paramenters
    batch_size: int,
    max_epochs: int,
    patience: int,
    accelerator: str | Accelerator,
) -> None:
    """Trains a model.

    Args:
        clini_table:
            An excel or csv file to read the clinical information from.
            Must at least have the columns specified in the arguments
            `patient_label` (containing a unique patient ID)
            and `ground_truth_label` (containing the ground truth to train for).
        slide_table:
            An excel or csv file to read the patient-slide associations from.
            Must at least have the columns specified in the arguments
            `patient_label` (containing the patient ID)
            and `filename_label`
            (containing a filename relative to `feature_dir`
            in which some of the patient's features are stored).
        feature_dir:
            See `slide_table`.
        output_dir:
            Path into which to output the artifacts (trained model etc.)
            generated during training.
        patient_label:
            See `clini_table`, `slide_table`.
        ground_truth_label:
            See `clini_table`.
        filename_label:
            See `slide_table`.
        categories:
            Categories of the ground truth.
            Set to `None` to automatically infer.
    """
    # Read and parse data from out clini and slide table
    patient_to_ground_truth = patient_to_ground_truth_from_clini_table_(
        clini_table_path=clini_table,
        ground_truth_label=ground_truth_label,
        patient_label=patient_label,
    )
    slide_to_patient = slide_to_patient_from_slide_table_(
        slide_table_path=slide_table,
        feature_dir=feature_dir,
        patient_label=patient_label,
        filename_label=filename_label,
    )

    # Clean data (remove slides without ground truth, missing features, etc.)
    patient_to_data = filter_complete_patient_data_(
        patient_to_ground_truth=patient_to_ground_truth,
        slide_to_patient=slide_to_patient,
        drop_patients_with_missing_ground_truth=True,
    )

    # Do a stratified train-validation split
    ground_truths = [patient_to_ground_truth[patient] for patient in patient_to_data]
    train_patients, valid_patients = cast(
        tuple[npt.NDArray[PatientId], npt.NDArray[PatientId]],
        train_test_split(list(patient_to_data), stratify=ground_truths, random_state=0),
    )

    train_dl, categories = dataloader_from_patient_data(
        patient_data=[patient_to_data[patient] for patient in train_patients],
        categories=categories,
        bag_size=bag_size,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
    )
    valid_dl, _ = dataloader_from_patient_data(
        patient_data=[patient_to_data[patient] for patient in valid_patients],
        bag_size=None,  # Use all the patient data for validation
        categories=categories,
        batch_size=1,
        shuffle=False,
        num_workers=num_workers,
    )
    if overlap := set(train_patients) & set(valid_patients):
        raise RuntimeError(
            f"unreachable: unexpected overlap between training and validation set: {overlap}"
        )

    # Sample one bag to infer the input dimensions of the model
    bags, bag_sizes, targets = cast(
        tuple[Bags, BagSizes, EncodedTargets], next(iter(train_dl))
    )
    _, _, dim_feats = bags.shape

    # Weigh classes inversely to their occurrence
    category_counts = cast(BagDataset, train_dl.dataset).ground_truths.sum(dim=0)
    category_weights = (x := category_counts.sum() / category_counts) / x.sum()

    if len(categories) <= 1:
        raise ValueError(f"not enough categories to train on: {categories}")
    elif any(category_counts < 16):
        underpopulated_categories = {
            category: count
            for category, count in zip(categories, category_counts, strict=True)
            if count < 16
        }
        raise ValueError(
            f"some categories do not have enough samples to meaningfully train a model: {underpopulated_categories}"
        )

    # Train the model
    model = LitVisionTransformer(
        categories=categories,
        category_weights=category_weights,
        dim_input=dim_feats,
        dim_model=512,
        dim_feedforward=2048,
        n_heads=8,
        n_layers=2,
        dropout=0.25,
        # Metadata, has no effect on model training
        ground_truth_label=ground_truth_label,
        train_patients=train_patients,
        valid_patients=valid_patients,
        clini_table=clini_table,
        slide_table=slide_table,
        feature_dir=feature_dir,
    )

    trainer = lightning.Trainer(
        default_root_dir=output_dir,
        callbacks=[
            EarlyStopping(monitor="validation_loss", mode="min", patience=patience),
            ModelCheckpoint(
                monitor="validation_loss",
                mode="min",
                filename="checkpoint-{epoch:02d}-{validation_loss:0.3f}",
            ),
        ],
        max_epochs=max_epochs,
        # FIXME The number of accelerators is currently fixed to one for the
        # following reasons:
        #  1. `trainer.predict()` does not return any predictions if used with
        #     the default strategy no multiple GPUs
        #  2. `barspoon.model.SafeMulticlassAUROC` breaks on multiple GPUs
        accelerator=accelerator,
        devices=1,
        gradient_clip_val=0.5,
        logger=CSVLogger(save_dir=output_dir),
    )

    trainer.fit(model=model, train_dataloaders=train_dl, val_dataloaders=valid_dl)
    trainer.save_checkpoint(output_dir / "model.ckpt")