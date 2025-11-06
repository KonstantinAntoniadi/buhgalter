import json
from typing import Any, Optional

from bank_clients.neolegoff_bank.models.auth import (
    AuthCompleteResponse,
    AuthNextStepResponse,
    AuthNextStepSmsResponse,
    AuthTokens,
    ResponseGetCipherKey,
)
from bank_clients.neolegoff_bank.models.auth.device_authorize import DeviceAuthorizeResponse
from bank_clients.neolegoff_bank.modules import AioNeolegoffCore
from bank_clients.neolegoff_bank.modules._helpers import prepare_response
from bank_clients.neolegoff_bank.modules._module_parent import AioNeolegoffModuleParent


def _log_response(response):
    print(response.json())

class AioNeolegoffAuth(AioNeolegoffModuleParent):
    def __init__(self, neolegoff: AioNeolegoffCore):
        super().__init__(neolegoff)

    @prepare_response(auth_required=False)
    async def auth_entry(self) -> AuthNextStepResponse:
        request_data = {
            "client_id": "tinkoff-mb-app",
            "redirect_uri": "mobile://",
            "response_type": "code",
            "response_mode": "json",
            "display": "json",
            "device_id": self.core.device_info.device_uid,
            "client_version": self.core.device_info.version,
            "vendor": "tinkoff_android",
            "claims": json.dumps(
                {
                    "id_token": {
                        "given_name": None,
                        "phone_number": None,
                        "picture": None,
                    }
                }
            ),
        }

        response = await self.core.session.post(
            url="https://id.tinkoff.ru/auth/authorize",
            data=request_data,
        )
        _log_response

        self.core.cookies = response.cookies

        return response

    @prepare_response(auth_required=False)
    async def auth_phone(self, phone: str, cid: str) -> AuthNextStepSmsResponse:
        request_data = {
            "phone": phone,
            "step": "phone",
            "fingerprint": self.core.device_info.fingerprint(),
        }
        
        response = await self.core.session.post(
            url=f"https://id.tinkoff.ru/auth/step?cid={cid}",
            data=request_data,
        )
        _log_response
        
        return response

    @prepare_response(auth_required=False)
    async def auth_sms_otp(
        self, otp: str, token: str, cid: str
    ) -> AuthNextStepResponse:
        request_data = {"otp": otp, "token": token, "step": "otp"}
        
        response = await self.core.session.post(
            url=f"https://id.tinkoff.ru/auth/step?cid={cid}",
            data=request_data,
        )
        _log_response
        return response

    async def auth_complete(
        self, cid: str
    ) -> AuthCompleteResponse | AuthNextStepResponse:
        request_data = {"step": "complete"}

        response = await self.core.session.post(
            url=f"https://id.tinkoff.ru/auth/step?cid={cid}",
            data=request_data,
        )
        _log_response
        response_dict: dict[str, Any] = response.json()

        if "action" in response_dict:
            to_return = AuthNextStepResponse(**response_dict)
            if to_return.is_error:
                raise ValueError(f"Error {to_return.error}: {to_return.error_message}")
            return AuthNextStepResponse(**response_dict)

        self.core.cookies = response.cookies

        return AuthCompleteResponse(**response_dict)

    @prepare_response(auth_required=False)
    async def auth_token(self, code: Optional[str] = None) -> AuthTokens:
        request_data = {
            "redirect_uri": "mobile://",
            "client_version": self.core.device_info.version,
            "vendor": "tinkoff_android",
        }
        if code is not None:
            request_data["grant_type"] = "authorization_code"
            request_data["code"] = code
            if "refresh_token" in request_data:
                del request_data["refresh_token"]
        elif self.core.tokens is not None:
            request_data.update(
                {
                    "grant_type": "refresh_token",
                    "refresh_token": self.core.tokens.refresh_token,
                    "device_id": self.core.device_info.device_uid,
                    "old_device_id": self.core.device_info.device_uid,
                    "vendor": "tinkoff_android",
                    "fingerprint": json.dumps(
                        {
                            "appVersion": self.core.device_info.app_version,
                            "authType": "pin",
                            "authTypeSetDate": "2022-10-11 12:20:37",
                            "autologinOn": True,
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
                            "mobileDeviceId": self.core.device_info.device_uid,
                            "mobileDeviceModel": self.core.device_info.device_model,
                            "mobileDeviceOs": "Android",
                            "mobileDeviceOsVersion": (
                                self.core.device_info.os_version_major
                            ),
                            "screenDpi": self.core.device_info.screen_dpi,
                            "screenHeight": self.core.device_info.screen_height,
                            "screenWidth": self.core.device_info.screen_width,
                            "tinkoffDeviceId": self.core.device_info.device_uid,
                            "userAgent": self.core.device_info.user_agent,
                        }
                    ),
                }
            )
        else:
            raise ValueError(f"{code=} and {self.core.tokens=}")

        response = await self.core.session.post(
            url="https://id.tinkoff.ru/auth/token",
            data=request_data,
            headers={"Authorization": "Basic dGlua29mZi1tYi1hcHA6"}, ## dGlua29mZi1tYi1hcHA6 = tinkoff-mb-app:
        )
        self.core.tokens = AuthTokens(**response.json())
        self.core.cookies = response.cookies

        self.core.session.headers.update(
            {"Authorization": f"Bearer {self.core.tokens.access_token}"}
        )

        return response

    @prepare_response(auth_required=False)
    async def get_device_cipher_key(self) -> ResponseGetCipherKey:
        response = await self.core.session.get(
            url="https://id.tinkoff.ru/account/api/v1/mobile/device_cipher_key",
        )

    @prepare_response(auth_required=False)
    async def auth_device(self) -> DeviceAuthorizeResponse:
        request_data = {
            "accessToken": self.core.tokens.access_token,
            "deviceId": self.core.device_info.device_uid,
            "fingerprint": self.core.device_info.device_fingerprint,
            "appVersion": self.core.device_info.app_version,
            "screen_height": self.core.device_info.screen_height,
            "root_flag": "false",
            "mobile_device_os_version": self.core.device_info.os_version_major,
            "screen_width": self.core.device_info.screen_width,
            "appName": "mobile",
            "origin": "mobile,ib5,loyalty,platform",
            "platform": "android",
            "mobile_device_model": "Mi 9T",
            "mobile_device_os": "android",
            "appsflyer_uid": self.core.device_info.appsflyer_uid,
            "connectionType": "WiFi",
            "screen_dpi": self.core.device_info.screen_dpi,
        }
        response = await self.core.session.post(
            url="https://api.tinkoff.ru/v1/device/authorize",
            data=request_data,
        )
        _log_response
        response_data = DeviceAuthorizeResponse(**response.json())
        self.core.session_info = response_data.payload
        self.core.app_data_manager.save_data()

        return response_data

    @prepare_response(auth_required=False)
    async def auth_authorize(self) -> AuthNextStepResponse:
        request_data = {
            "client_id": "tinkoff-mb-app",
            "device_id": self.core.device_info.device_uid,
            "response_type": "code",
            "redirect_uri": "mobile://",
            "response_mode": "json",
            "display": "json",
            "prompt": "password",
            "client_version": self.core.device_info.version,
            "vendor": "tinkoff_android",
            "claims": json.dumps(
                {
                    "id_token": {
                        "given_name": None,
                        "phone_number": None,
                        "picture": None,
                    }
                }
            ),
        }
        
        response = await self.core.session.post(
            url="https://id.tinkoff.ru/auth/authorize",
            data=request_data,
        )
        _log_response(response)
        return response

    @prepare_response(auth_required=False)
    async def auth_password(self, password: str, cid: str) -> AuthNextStepResponse:
        request_data = {
            "password": password,
            "step": "password",
        }
        
        # return response
        return await self.core.session.post(
            url=f"https://id.tinkoff.ru/auth/step?cid={cid}",
            data=request_data,
        )

    @prepare_response(auth_required=False)
    async def auth_fingerprint(self, cid: str) -> AuthNextStepResponse:
        request_data = {
            "step": "fingerprint",
            "fingerprint": self.core.device_info.fingerprint(),
        }
        response = await self.core.session.post(
            url=f"https://id.tinkoff.ru/auth/step?cid={cid}",
            data=request_data,
        )
        _log_response(response)
        return response

    @prepare_response(auth_required=False)
    async def auth_card(self, cid: str, card: str) -> AuthNextStepResponse:
        request_data = {
            "card": card,
            "cardInputType": "manual",
            "step": "card",
        }

        response = await self.core.session.post(
            url=f"https://id.tinkoff.ru/auth/card?cid={cid}",
            data=request_data,
        )
        _log_response(response)
        return response

    @prepare_response(auth_required=False)
    async def auth_set_password(self, cid: str, password: str) -> AuthCompleteResponse:
        request_data = {
            "password": password,
            "step": "set-password",
        }

        response = await self.core.session.post(
            url=f"https://id.tinkoff.ru/auth/update?cid={cid}",
            data=request_data,
        )
        _log_response(response)
        return response

    async def login_pipeline(
        self, phone_number: str, password: str, card_number: str | None = None
    ):
        """

        :param phone_number: `79998887766` format
        :param password:
        :param card_number:
        :return:
        """
        print(f"is_login_required {self._neolegoff.is_login_required}")
        if self._neolegoff.is_login_required:
            response = await self.auth_entry()
            _log_response
            while isinstance(response, AuthNextStepResponse):
                if response.step == "entry":
                    response = await self.auth_phone(phone_number, response.cid)
                    _log_response(response)
                elif response.step == "otp":
                    code = yield
                    yield
                    response = await self.auth_sms_otp(
                        code, response.token, response.cid
                    )
                    _log_response(response)
                elif response.step == "password":
                    response = await self.auth_password(password, response.cid)
                    _log_response(response)
                elif response.step == "fingerprint":
                    response = await self.auth_fingerprint(response.cid)
                    _log_response(response)
                elif response.step == "complete":
                    response = await self.auth_complete(response.cid)
                    _log_response(response)
                else:
                    print(f"response = {response}")
                    break

            if isinstance(response, AuthCompleteResponse):
                print("response is AuthCompleteResponse")
                await self.auth_token(response.code)
                await self.get_device_cipher_key()
                await self.auth_device()

            response = await self.auth_authorize()
            _log_response
            while isinstance(response, AuthNextStepResponse):
                _log_response
                if response.step == "password":
                    response = await self.auth_password(password, response.cid)
                    _log_response
                elif response.step == "fingerprint":
                    response = await self.auth_fingerprint(response.cid)
                    _log_response
                elif response.step == "card":
                    response = await self.auth_card(response.cid, card_number)
                    _log_response
                elif response.step == "set-password":
                    response = await self.auth_set_password(response.cid, password)
                    _log_response
                elif response.step == "complete":
                    response = await self.auth_complete(response.cid)
                    _log_response
                elif response.step == "entry":
                    continue
            if isinstance(response, AuthCompleteResponse):
                await self.auth_token(response.code)
                await self.get_device_cipher_key()

        await self.auth_device()
        return

    async def authorize(self):
        await self.auth_token()
        await self.get_device_cipher_key()
        await self.auth_device()

    async def login(self, phone, password, card):
        async def get_sms_code():
            return input("SMS code >>> ")

        login_pipeline = self.login_pipeline(phone, password, card)
        async for _ in login_pipeline:
            await login_pipeline.asend(await get_sms_code())
