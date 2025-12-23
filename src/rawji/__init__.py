"""Rawji - Fujifilm RAW Conversion Tool - Convert RAF files using in-camera processing."""

__version__ = "0.1.0"

from .fuji_enums import FilmSimulation, WhiteBalance, DynamicRange
from .fuji_usb import FujiCamera
from .fuji_profile import create_profile_from_camera, validate_params

__all__ = [
    "FilmSimulation",
    "WhiteBalance",
    "DynamicRange",
    "FujiCamera",
    "create_profile_from_camera",
    "validate_params",
]
