from sales_data_platform_azure import __version__, contracts, quality, transformation


def test_foundation_packages_are_importable() -> None:
    assert __version__ == "0.1.0"
    assert contracts.__doc__
    assert quality.__doc__
    assert transformation.__doc__
