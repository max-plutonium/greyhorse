from greyhorse.app.entities.application import Application
from greyhorse.app.schemas.components import ModuleComponentConf, ModuleConf

from ..conf import SQLITE_URI

app_conf = ModuleConf(
    enabled=True,
    components={
        'submodule': ModuleComponentConf(
            enabled=True, path='..module', args={'dsn': SQLITE_URI}
        )
    },
)

app = Application('TestApp')

assert app.load(app_conf)
