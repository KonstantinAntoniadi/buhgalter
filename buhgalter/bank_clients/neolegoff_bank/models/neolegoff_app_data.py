import hashlib
import json
import string
import pickle
from abc import ABC
from base64 import b64decode, b64encode
from datetime import datetime, timezone
from hashlib import md5
from ipaddress import IPv4Address, IPv4Network
from pathlib import Path
from random import choice, randint, randrange
from typing import Optional

from appdirs import AppDirs
from Cryptodome.Cipher import AES
from pydantic import BaseModel, Field
from randmac import RandMac

from bank_clients.neolegoff_bank.models.auth import AuthTokens
from bank_clients.neolegoff_bank.models.auth.device_authorize import DeviceAuthorizeResponsePayload


class NeolegoffDeviceInfo(BaseModel):
    # May need an increase
    app_version = "6.12.1"
    version = "3.1.2"

    # Unique device IDs
    appsflyer_uid = "1665453203890-5636190662334170798"
    device_uid = "8b102654eb77ddcc"
    installation_uid = "34snDzQ2mYDRnfrenBai"
    old_device_id = "8b102654eb77ddcc"

    # Device info
    device_model = "WhiteApfel Neolegoff"

    screen_dpi = 404
    screen_height = 2297
    screen_width = 1080

    # Android info
    os_version_major = 12

    # Calculated
    user_agent = f"{device_model}/android: {os_version_major}/TCSMB/{app_version}"
    device_fingerprint = (
        f"{user_agent}###{screen_width}x{screen_height}x32###180###false###false###"
    )

    @classmethod
    def generate_new_config(cls):
        return cls(
            appsflyer_uid=(
                f"{''.join(str(randint(0, 9)) for _ in range(13))}-{''.join(str(randint(0, 9)) for _ in range(19))}"
            ),
            device_uid=(
                device_uid := "".join(
                    [choice(string.hexdigits[:-6]) for _ in range(16)]
                )
            ),
            old_device_id=device_uid,
            installation_uid="".join(
                [choice(string.ascii_letters + string.digits)
                 for _ in range(20)]
            ),
        )

    def fingerprint(self):
        return json.dumps(
            {
                "appVersion": self.app_version,
                "autologinOn": False,
                "autologinUsed": False,
                "backCameraAvailable": True,
                "biometricsSupport": 1,
                "clientLanguage": "en",
                "clientTimezone": -180,
                "connectionType": "WiFi",
                "debug": 0,
                "emulator": 0,
                "frontCameraAvailable": True,
                "root_flag": False,
                "lockedDevice": 1,
                "mobileDeviceId": self.device_uid,
                "mobileDeviceModel": self.device_model,
                "mobileDeviceOs": "Android",
                "mobileDeviceOsVersion": "12",
                "screenDpi": self.screen_dpi,
                "screenHeight": self.screen_height,
                "screenWidth": self.screen_width,
                "tinkoffDeviceId": self.device_uid,
                "userAgent": self.user_agent,
            }
        )


class NeolegoffAppData(BaseModel):
    app_name: str = Field("main:whiteapfel")
    cookies: dict = Field(default_factory=dict)
    cypher_key: Optional[str]
    device_info: Optional[NeolegoffDeviceInfo]
    session_info: Optional[DeviceAuthorizeResponsePayload]
    tokens: Optional[AuthTokens]


class NeolegoffAppDataManagerAbstract(ABC):
    def __init__(self, **kwargs):
        ...

    def update_tokens(self, tokens: AuthTokens):
        ...

    def update_device_info(self, device_info: NeolegoffDeviceInfo):
        ...

    def update_cookies(self, cookies: dict):
        ...

    def update_session_info(self, session: DeviceAuthorizeResponsePayload):
        ...

    def load_data(self, **kwargs):
        ...

    def save_data(self, **kwargs):
        ...


class NeolegoffAppDataManagerFileSystem(NeolegoffAppDataManagerAbstract):
    def __init__(self, base64_secret_key: str, app_data: NeolegoffAppData = None, **kwargs):
        super().__init__()
        self.data: NeolegoffAppData = app_data

        self.salt = md5(b"whiteapfel").hexdigest().encode()
        self.key = hashlib.scrypt(
            self.data.app_name.rsplit(":", 1)[-1].encode(),
            salt=self.salt,
            n=2,
            r=8,
            p=2,
            dklen=32,
        )
        self.base64_secret_key = base64_secret_key

        self.last_load_datetime: datetime = None

    @property
    def data_dir_path(self) -> Path:
        neolegoff_dir = AppDirs("neolegofff", "whiteapfel")
        return Path(
            f"{neolegoff_dir.user_data_dir}/{self.data.app_name.rsplit(':', 1)[0]}"
        )

    @property
    def data_file_path(self) -> Path:
        return self.data_dir_path / "neolegoff_data.json"

    @property
    def file_last_modified_datetime(self) -> datetime:
        return datetime.fromtimestamp(
            self.data_file_path.stat().st_mtime, tz=timezone.utc
        )

    def get_cipher(self):
        return AES.new(self.key, AES.MODE_EAX, b64decode(self.base64_secret_key))

    def load_data(self, **kwargs):
        self.data_dir_path.mkdir(parents=True, exist_ok=True)

        if not self.data_file_path.exists():
            self.data.device_info = NeolegoffDeviceInfo.generate_new_config()
            self.save_data()
        else:
            encoded_b64_string = self.data_file_path.read_text()
            encrypted_string = b64decode(encoded_b64_string)
            tag, ciphertext = encrypted_string[:16], encrypted_string[16:]
            json_string = self.get_cipher().decrypt_and_verify(ciphertext, tag)
            data = json.loads(json_string)

            self.data = NeolegoffAppData(**data)
            self.last_load_datetime = self.file_last_modified_datetime
        return self

    def save_data(self, **kwargs):
        json_string = self.data.json(by_alias=True)
        ciphertext, tag = self.get_cipher().encrypt_and_digest(json_string.encode())
        encrypted_string = tag + ciphertext
        encoded_b64_string = b64encode(encrypted_string).decode()
        self.data_file_path.write_text(encoded_b64_string)
        self.last_load_datetime = self.file_last_modified_datetime

    def update_tokens(self, tokens: AuthTokens):
        self.data.tokens = tokens
        self.save_data()

    def update_device_info(self, device_info: NeolegoffDeviceInfo):
        self.data.device_info = device_info
        self.save_data()

    def update_cookies(self, cookies: dict):
        self.data.cookies.update(cookies)
        self.save_data()

    def update_session_info(self, session_info: DeviceAuthorizeResponsePayload):
        self.data.session_info = session_info
        self.save_data()
