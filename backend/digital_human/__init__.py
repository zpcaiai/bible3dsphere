"""Bible-grounded digital-human domain package."""

__all__ = ["DigitalHumanService"]


def __getattr__(name: str):
    if name != "DigitalHumanService":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    # A transcription Worker does not need the domain catalog or release verifier.
    from .service import DigitalHumanService

    globals()[name] = DigitalHumanService
    return DigitalHumanService
