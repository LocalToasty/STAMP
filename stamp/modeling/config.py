from pathlib import Path

from pydantic import AliasChoices, BaseModel, Field


class TrainConfig(BaseModel):
    clini_table: Path
    slide_table: Path
    feature_dir: Path
    output_dir: Path
    target_label: str = Field(pattern="^[a-zA-Z0-9_]+$")
    categories: list[str] | None = None
    cat_labels: list[str] | None = None
    cont_labels: list[str] | None = None


class CrossvalConfig(TrainConfig):
    n_splits: int = Field(ge=2)


class DeploymentConfig(BaseModel):
    clini_table: Path
    slide_table: Path
    output_dir: Path
    feature_dir: Path = Field(
        validation_alias=AliasChoices("feature_dir", "default_feature_dir")
    )
    target_label: str = Field(pattern="^[a-zA-Z0-9_]+$")
    cat_labels: list[str] | None = None
    cont_labels: list[str] | None = None
    # We can't have things called `model_` in pydantic, so let's call it `checkpoint_path` instead
    checkpoint_path: Path = Field(
        validation_alias=AliasChoices("model_path", "checkpoint_path")
    )