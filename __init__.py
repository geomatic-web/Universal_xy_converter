import os


def classFactory(iface):
    from .bftm_converter import UniversalXYConverter

    try:
        from .startup import preload_crs

        preload_crs()
    except:
        pass

    return UniversalXYConverter(iface)
