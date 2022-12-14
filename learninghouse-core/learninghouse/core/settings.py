from functools import lru_cache
from pathlib import Path
from secrets import token_hex
from typing import Any, Dict, Optional, Union

from pydantic import BaseSettings, DirectoryPath

from learninghouse import versions
from learninghouse.api.errors import (LearningHouseException,
                                      LearningHouseValidationError)
from learninghouse.core.logging import LoggingLevelEnum
from learninghouse.models.base import EnumModel

LICENSE_URL = 'https://github.com/LearningHouseService/learninghouse-monorepo/blob/master/LICENSE'


class ServiceSettings(BaseSettings):
    debug: bool = False
    docs_url: str = '/docs'
    openapi_file: str = '/learninghouse_api.json'
    title: str = 'learningHouse Service'

    host: str = '127.0.0.1'
    port: int = 5000
    reload: bool = False
    base_url: Optional[str]

    environment: str = 'production'

    config_directory: DirectoryPath = './brains'

    logging_level: LoggingLevelEnum = LoggingLevelEnum.INFO

    jwt_secret: str = token_hex(16)
    jwt_expire_minutes: int = 10

    class Config:  # pylint: disable=too-few-public-methods
        validate_assignment = True
        env_file = '.env'
        env_prefix = 'learninghouse_'

    @property
    def fastapi_kwargs(self) -> Dict[str, Any]:
        return {
            'debug': self.debug,
            'title': self.title,
            'openapi_url': self.openapi_file,
            'docs_url': None,
            'redoc_url': None,
            'version': versions.service,
            'responses': {
                LearningHouseValidationError.STATUS_CODE:
                LearningHouseValidationError.api_description(),
                LearningHouseException.STATUS_CODE:
                LearningHouseException.api_description()
            },
            'license_info':  {
                'name': 'MIT License',
                    'url': LICENSE_URL
            }
        }

    @property
    def uvicorn_kwargs(self) -> Dict[str, Any]:
        kwargs = {
            'host': self.host,
            'port': self.port,
            'headers': [('server', f'LearningHouse Service {versions.service}')]
        }

        if self.reload:
            kwargs['reload'] = True

        return kwargs

    @property
    def brains_directory(self) -> Path:
        return Path(self.config_directory).absolute()

    @property
    def base_url_calculated(self) -> str:
        if self.base_url:
            base_url = self.base_url
        elif self.host in ('0.0.0.0', '127.0.0.1'):
            base_url = 'http://localhost'
        else:
            base_url = f'http://{self.host}'

        return f'{base_url}:{self.port}'

    @property
    def documentation_url(self) -> Union[str, None]:
        documentation_url = None

        if self.docs_url is not None:
            documentation_url = self.base_url_calculated + self.docs_url

        return documentation_url

    @property
    def openapi_url(self) -> str:
        return self.base_url_calculated + self.openapi_file

    @property
    def jwt_payload_claims(self) -> Dict[str, str]:
        return {
            'audience': 'LearningHouseAPI',
            'issuer': 'LearningHouse Service'
        }


class DevelopmentSettings(ServiceSettings):
    environment: str = 'development'
    debug: bool = True
    reload: bool = True
    title: str = 'learningHouse Service - Development'
    api_key_required: bool = False

    class Config(ServiceSettings.Config):  # pylint: disable=too-few-public-methods
        env_file = '.env'
        env_prefix = 'learninghouse_'


class ServiceEnvironment(str, EnumModel):
    PROD = 'production', ServiceSettings
    DEV = 'development', DevelopmentSettings

    def __init__(self,
                 description: str,
                 settings_class: ServiceSettings):
        # pylint: disable=super-init-not-called
        self._description: str = description
        self._settings_class: ServiceSettings = settings_class

    @property
    def description(self) -> str:
        return self._description

    @property
    def settings_class(self) -> ServiceSettings:
        return self._settings_class


class ServiceBaseSettings(BaseSettings):
    environment: ServiceEnvironment = ServiceEnvironment.PROD

    class Config:  # pylint: disable=too-few-public-methods
        env_file = '.env'
        env_prefix = 'learninghouse_'


@lru_cache()
def service_settings() -> ServiceSettings:
    environment = ServiceBaseSettings().environment
    return environment.settings_class()
