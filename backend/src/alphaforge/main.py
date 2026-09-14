from alphaforge.api.app import create_app
from alphaforge.core.config import get_settings

settings = get_settings()
app = create_app(settings)
