import re
from pathlib import Path

import alembic
import alembic.command
import alembic.config


class MigrationOperator:
    TABLE_CONTENTS_RE = re.compile(
        r'^\s+(comment=|sa.Column|sa.PrimaryKeyConstraint|'
        r'sa.ForeignKeyConstraint|sa.UniqueConstraint|sa.CheckConstraint).+'
    )

    def __init__(self, dsn: str, alembic_path: Path):
        self._alembic_path = alembic_path
        self._db_dsn = dsn

    def init(self, metadata_package: str, metadata_name: str = 'metadata'):
        """
        Initialize migration directory
        """
        config = alembic.config.Config(self._alembic_path / 'alembic.ini')
        config.set_main_option('script_location', str(self._alembic_path))
        config.set_main_option('sqlalchemy.url', self._db_dsn)

        alembic.command.init(config, str(self._alembic_path), package=True)

        env_path = self._alembic_path / 'env.py'
        lines = list()

        with env_path.open('r') as f:
            for line in f.readlines():
                if line == 'from alembic import context\n':
                    lines.append(line)
                    lines.append('from greyhorse_sqla.migration import utils')
                    if metadata_name != 'metadata':
                        metadata_name += ' as metadata'
                    lines.append(f'from {metadata_package} import {metadata_name}\n')
                elif line == 'target_metadata = None\n':
                    lines.append('target_metadata = metadata\n')
                elif line == '        literal_binds=True,\n':
                    lines.append('        literal_binds=False,\n')
                elif line == '        dialect_opts={"paramstyle": "named"},\n':
                    lines.append('        include_schemas=True,\n')
                    lines.append(line.replace('"', '\''))
                elif line == '            connection=connection, target_metadata=target_metadata\n':
                    lines.append('            connection=connection, target_metadata=target_metadata,\n')
                    lines.append('            version_table_schema=target_metadata.schema,\n')
                    lines.append('            include_schemas=True,\n')
                    lines.append('            render_item=utils.render_item,\n')
                elif line == '        with context.begin_transaction():\n':
                    lines.append(line)
                    lines.append(
                        '            if \'postgresql\' == connectable.dialect.name and target_metadata.schema:\n')
                    lines.append(
                        '                connection.execute(f\'CREATE SCHEMA IF NOT EXISTS "{target_metadata.schema}" '
                        'AUTHORIZATION CURRENT_USER\')\n')
                    lines.append(
                        '                connection.execute(f\'set search_path to "{target_metadata.schema}", '
                        'public\')\n')
                else:
                    lines.append(line)

        with env_path.open('w') as f:
            f.writelines(lines)

    def new(self, name: str):
        """
        Generate new revision file
        """
        versions_dir = self._alembic_path / 'versions'
        files_count = len(list(versions_dir.glob('*.py')))
        revision = f'{files_count:03d}'

        config = alembic.config.Config(self._alembic_path / 'alembic.ini')
        config.set_main_option('script_location', str(self._alembic_path))
        config.set_main_option('sqlalchemy.url', self._db_dsn)

        scripts = alembic.command.revision(config, message=name, autogenerate=True, rev_id=revision)
        if not isinstance(scripts, list):
            scripts = [scripts]

        for script in scripts:
            path = Path(script.path)
            lines = list()

            with path.open('r') as f:
                for line in f.readlines():
                    line = line.replace('op.create_table(', 'op.create_table(\n' + ' ' * 8)
                    line = re.sub(self.TABLE_CONTENTS_RE, lambda _: ' ' * 4 + line.rstrip(), line)
                    lines.append(line)

            with path.open('w') as f:
                f.writelines(lines)

    def upgrade(self, offline: bool = False):
        """
        Upgrade database to head
        """
        config = alembic.config.Config()
        config.set_main_option('script_location', str(self._alembic_path))
        config.set_main_option('sqlalchemy.url', self._db_dsn)

        alembic.command.upgrade(config, revision='head', sql=offline)

    def downgrade(self, offline: bool = False):
        """
        Downgrade database for one step
        """
        config = alembic.config.Config()
        config.set_main_option('script_location', str(self._alembic_path))
        config.set_main_option('sqlalchemy.url', self._db_dsn)
        revision = 'head:-1' if offline else '-1'

        alembic.command.downgrade(config, revision=revision, sql=offline)
