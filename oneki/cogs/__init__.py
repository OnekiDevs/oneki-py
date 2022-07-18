from pkgutil import iter_modules

initial_extensions = [
    module.name for module in iter_modules(__path__, f"{__package__}.") if not module.name.startswith("_")
]

dev_extensions = [
    module.name for module in iter_modules(__path__, f"{__package__}.") if module.name.startswith("_")
]
