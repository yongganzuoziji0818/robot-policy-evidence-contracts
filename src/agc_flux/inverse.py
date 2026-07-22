"""Dependency-free analytic model used by the frozen FLUX-v8 G0.

The model deliberately implements only the theorem family. It is not a plume
simulator and must not be used as natural or formal evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Sequence

Vector2 = tuple[float, float]
Matrix2 = tuple[Vector2, Vector2]


def _dot(left: Vector2, right: Vector2) -> float:
    return left[0] * right[0] + left[1] * right[1]


def determinant_2x2(matrix: Matrix2) -> float:
    return matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0]


def information_matrix(
    rows: Iterable[tuple[Vector2, float]],
) -> Matrix2:
    """Return sum J_i^T J_i / sigma_i^2 for scalar observations."""

    i00 = i01 = i11 = 0.0
    for gradient, sigma in rows:
        if not math.isfinite(sigma) or sigma <= 0.0:
            raise ValueError("observation sigma must be finite and positive")
        weight = 1.0 / (sigma * sigma)
        i00 += weight * gradient[0] * gradient[0]
        i01 += weight * gradient[0] * gradient[1]
        i11 += weight * gradient[1] * gradient[1]
    return ((i00, i01), (i01, i11))


def min_eigenvalue_2x2(matrix: Matrix2) -> float:
    trace = matrix[0][0] + matrix[1][1]
    discriminant = math.hypot(matrix[0][0] - matrix[1][1], 2.0 * matrix[0][1])
    value = 0.5 * (trace - discriminant)
    return 0.0 if -1e-15 < value < 0.0 else value


def nullspace_projected_information(
    aerial_gradient: Vector2,
    candidate_rows: Iterable[tuple[Vector2, float]],
) -> float:
    """Information supplied along the one-dimensional aerial nullspace."""

    norm = math.hypot(*aerial_gradient)
    if norm <= 0.0 or not math.isfinite(norm):
        raise ValueError("aerial gradient must be finite and nonzero")
    null_vector = (-aerial_gradient[1] / norm, aerial_gradient[0] / norm)
    gain = 0.0
    for gradient, sigma in candidate_rows:
        if not math.isfinite(sigma) or sigma <= 0.0:
            raise ValueError("observation sigma must be finite and positive")
        projection = _dot(null_vector, gradient)
        gain += projection * projection / (sigma * sigma)
    return gain


@dataclass(frozen=True)
class FluxModel:
    diffusion: float
    loss_rate: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.diffusion) or self.diffusion <= 0.0:
            raise ValueError("diffusion must be finite and positive")
        if not math.isfinite(self.loss_rate) or self.loss_rate <= 0.0:
            raise ValueError("loss_rate must be finite and positive")

    @property
    def decay(self) -> float:
        return math.sqrt(self.loss_rate / self.diffusion)

    @property
    def escape_coefficient(self) -> float:
        return math.sqrt(self.diffusion * self.loss_rate)

    def _validate_parameters(self, source: float, deposition: float) -> None:
        if not math.isfinite(source) or source <= 0.0:
            raise ValueError("source must be finite and positive")
        if not math.isfinite(deposition) or deposition < 0.0:
            raise ValueError("deposition must be finite and nonnegative")

    def surface_amplitude(self, source: float, deposition: float) -> float:
        self._validate_parameters(source, deposition)
        return source / (self.escape_coefficient + deposition)

    def concentration(self, height: float, source: float, deposition: float) -> float:
        if not math.isfinite(height) or height < 0.0:
            raise ValueError("height must be finite and nonnegative")
        amplitude = self.surface_amplitude(source, deposition)
        return amplitude * math.exp(-self.decay * height)

    def deposition_flux(self, source: float, deposition: float) -> float:
        return deposition * self.surface_amplitude(source, deposition)

    def equivalent_source(self, amplitude: float, deposition: float) -> float:
        if not math.isfinite(amplitude) or amplitude <= 0.0:
            raise ValueError("amplitude must be finite and positive")
        if not math.isfinite(deposition) or deposition < 0.0:
            raise ValueError("deposition must be finite and nonnegative")
        return amplitude * (self.escape_coefficient + deposition)

    def recover(
        self, height: float, aerial_concentration: float, ground_flux: float
    ) -> tuple[float, float]:
        if not math.isfinite(height) or height < 0.0:
            raise ValueError("height must be finite and nonnegative")
        if not math.isfinite(aerial_concentration) or aerial_concentration <= 0.0:
            raise ValueError("aerial_concentration must be finite and positive")
        if not math.isfinite(ground_flux) or ground_flux < 0.0:
            raise ValueError("ground_flux must be finite and nonnegative")
        amplitude = aerial_concentration * math.exp(self.decay * height)
        deposition = ground_flux / amplitude
        source = self.escape_coefficient * amplitude + ground_flux
        return source, deposition

    def aerial_gradient(
        self, height: float, source: float, deposition: float
    ) -> Vector2:
        self._validate_parameters(source, deposition)
        if not math.isfinite(height) or height < 0.0:
            raise ValueError("height must be finite and nonnegative")
        scale = math.exp(-self.decay * height)
        denominator = self.escape_coefficient + deposition
        return (
            scale / denominator,
            -scale * source / (denominator * denominator),
        )

    def ground_flux_gradient(self, source: float, deposition: float) -> Vector2:
        self._validate_parameters(source, deposition)
        denominator = self.escape_coefficient + deposition
        return (
            deposition / denominator,
            source * self.escape_coefficient / (denominator * denominator),
        )

    def aerial_rows(
        self,
        heights: Sequence[float],
        source: float,
        deposition: float,
        sigma: float,
    ) -> tuple[tuple[Vector2, float], ...]:
        return tuple(
            (self.aerial_gradient(height, source, deposition), sigma)
            for height in heights
        )
