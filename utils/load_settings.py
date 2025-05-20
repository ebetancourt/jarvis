#!/usr/bin/env python3
import yaml


def load_settings():
    """Load settings from settings.yml."""
    with open("settings.yml", "r") as file:
        return yaml.safe_load(file)
