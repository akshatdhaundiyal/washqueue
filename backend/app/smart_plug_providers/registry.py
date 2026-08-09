from typing import Dict, Type
try:
    from app.smart_plug_providers.base import SmartPlugProvider
    from app.smart_plug_providers.tuya_local import TuyaLocalProvider
except ImportError:
    from smart_plug_providers.base import SmartPlugProvider
    from smart_plug_providers.tuya_local import TuyaLocalProvider

_PROVIDERS: Dict[str, Type[SmartPlugProvider]] = {}

def register_provider(name: str, provider_cls: Type[SmartPlugProvider]):
    _PROVIDERS[name.lower()] = provider_cls

def get_provider(name: str) -> SmartPlugProvider:
    provider_key = name.lower()
    if provider_key not in _PROVIDERS:
        raise ValueError(f"Unknown smart plug provider: '{name}'. Registered: {list(_PROVIDERS.keys())}")
    return _PROVIDERS[provider_key]()

# Auto-register default providers
register_provider("tuya_local", TuyaLocalProvider)
register_provider("wipro", TuyaLocalProvider)  # Wipro uses Tuya local protocol
