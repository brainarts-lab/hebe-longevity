"""Loaded by Hermes as a standalone module. Imports Hebe's own package without changing sys.path."""
import hashlib
import importlib.util
from pathlib import Path
import sys

package = Path(__file__).resolve().parents[1] / 'hebe'
namespace = '_brainarts_hebe_' + hashlib.sha256(str(package).encode()).hexdigest()[:16]
if namespace not in sys.modules:
    spec = importlib.util.spec_from_file_location(namespace, package / '__init__.py', submodule_search_locations=[str(package)])
    module = importlib.util.module_from_spec(spec)
    sys.modules[namespace] = module
    spec.loader.exec_module(module)
api = __import__(namespace + '.api', fromlist=['create_router'])


def home():
    from plugins.plugin_storage import plugin_data_dir
    return plugin_data_dir('hebe-longevity')


router = api.create_router(home)
