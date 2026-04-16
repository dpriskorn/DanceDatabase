"""Reusable pipeline components for data source workflows."""
import json
import logging
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PipelineStep(BaseModel):
    """A single step in a data pipeline."""

    name: str
    func: Callable
    input_files: list[Path] = Field(default_factory=list)
    output_files: list[Path] = Field(default_factory=list)
    model_config = {"arbitrary_types_allowed": True}

    def _has_content(self, f: Path) -> bool:
        """Check if file exists and has content (not empty)."""
        if not f.exists():
            return False
        if f.suffix == ".json":
            try:
                content = f.read_text()
                if content in ("[]", "{}", ""):
                    return False
                data = json.loads(content)
                if isinstance(data, (list, dict)) and len(data) == 0:
                    return False
            except json.JSONDecodeError:
                pass
        return True

    def needs_run(self, force: bool = False) -> bool:
        """Check if step needs to run (missing input OR missing output OR empty input)."""
        if force:
            return True
        if not self.input_files:
            return not all(f.exists() for f in self.output_files) if self.output_files else True
        if any(not f.exists() for f in self.input_files):
            return True
        if any(not self._has_content(f) for f in self.input_files):
            return True
        if not self.output_files:
            return True
        return any(not f.exists() for f in self.output_files)

    def run(self, force: bool = False) -> None:
        """Run the step if needed."""
        print(f"\n[RUN] {self.name}")
        self.func()


class Pipeline(BaseModel):
    """A pipeline that runs multiple steps in sequence."""

    name: str
    steps: list[PipelineStep] = Field(default_factory=list)
    model_config = {"arbitrary_types_allowed": True}

    def add_step(
        self,
        name: str,
        func: Callable,
        input_files: list[Path] | None = None,
        output_files: list[Path] | None = None,
    ) -> None:
        """Add a step to the pipeline."""
        self.steps.append(
            PipelineStep(
                name=name,
                func=func,
                input_files=input_files or [],
                output_files=output_files or [],
            )
        )

    def run(self, only_scrape: bool = False) -> None:
        """Run all steps in sequence."""
        for step in self.steps:
            step.run()
