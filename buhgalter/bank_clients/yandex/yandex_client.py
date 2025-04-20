import requests
import pickle
import hashlib
import uuid
import json
import asyncio
from hashlib import md5
from base64 import b64decode, b64encode
from decimal import Decimal
from pathlib import Path

from appdirs import AppDirs
from Cryptodome.Cipher import AES

from bank_clients.yandex.models.product import *
from bank_clients.yandex.models.operations import *
from utils.image import *


class YandexClient:
    def __init__(self, tg_client, base64_key):
        self.login = None
        self.session = requests.Session()
        self.csrf_token = None
        self.track_id = None
        self.products = []
        self.is_need_auth = True
        self.bank_domain = "https://bank.yandex.ru"
        self.tg_client = tg_client
        self.salt = md5(b"yandex_bank").hexdigest().encode()
        self.app_name = "main5:yandex_bank"
        self.key = hashlib.scrypt(
            self.app_name.rsplit(":", 1)[-1].encode(),
            salt=self.salt,
            n=2,
            r=8,
            p=2,
            dklen=32,
        )
        self.base64_key = base64_key

    @property
    def data_dir_path(self) -> Path:
        yandex_bank_dir = AppDirs("yandex_bank", "kantoniadi")
        return Path(
            f"{yandex_bank_dir.user_data_dir}/{self.app_name.rsplit(':', 1)[0]}"
        )

    @property
    def data_file_path(self) -> Path:
        return self.data_dir_path / "yandex_bank_data.pkl"

    async def _get_cookies(self):
        response = self.session.post(
            url="https://passport.yandex.ru/registration-validations/auth/accounts",
        )

        self.csrf_token = response.json()["csrf"]
        print(response.text)

    async def _auth_start(self, login: str):

        process_uid = str(uuid.uuid4())

        response = self.session.post(
            url="https://passport.yandex.ru/registration-validations/auth/multi_step/start",
            data={
                "login": login,
                "process_uuid": process_uid,
                "origin": "user_id",
                "csrf_token": self.csrf_token,
                "check_for_xtokens_for_pictures": 1,
                "can_send_push_code": 1,
            },
        )
        print(response.text)

        print("start_2")
        response = self.session.post(
            url="https://passport.yandex.ru/registration-validations/auth/multi_step/start",
            data={
                "login": login,
                "process_uuid": process_uid,
                "origin": "user_id",
                "csrf_token": self.csrf_token,
            },
        )
        self.track_id = response.json()["track_id"]
        print(response.text)

        await self._get_cookies()

    async def _auth_submit(self):
        response = self.session.post(
            url="https://passport.yandex.ru/registration-validations/auth/password/submit",
            data={"csrf_token": self.csrf_token,
                  "qrWithLoginTrackId": self.track_id},
        )
        self.csrf_token = response.json()["csrf_token"]
        print(response.text)

    async def _get_qr_code_for_login(self):
        response = self.session.get(
            url="https://passport.yandex.ru/auth/magic/code/",
            params={
                "track_id": self.track_id,
            },
        )
        qr_svg_code = response.text
        path_out = "output.png"
        svg_to_png(svg=qr_svg_code, path_out=path_out)
        await self.tg_client.send_image(path_out)
        print(response)

    async def _check_status_authorize(self):
        print("Проверка статуса")
        status = {}
        while status == {}:
            response = self.session.post(
                url="https://passport.yandex.ru/auth/new/magic/status/",
                data={"track_id": self.track_id,
                      "csrf_token": self.csrf_token},
            )
            status = response.json()
            await asyncio.sleep(0.5)
        print(response.text)

    async def _yandex_bank_auth(self):
        print("авторизация в Я банке")
        response = self.session.post(
            url="https://bank.yandex.ru/web-sdk/api/startSession",
            params={"consumerId": "YANDEX_ID"},
            json={},
        )
        print(response.text)
        return response

    def get_cipher(self):
        return AES.new(self.key, AES.MODE_EAX, b64decode(self.base64_key))

    def _save_session(self):
        cookies = pickle.dumps(self.session.cookies)
        ciphertext, tag = self.get_cipher().encrypt_and_digest(cookies)
        encrypted_string = tag + ciphertext
        encoded_b64_string = b64encode(encrypted_string).decode()
        self.data_file_path.write_text(encoded_b64_string)
        print("Сессия сохранена.")

    async def authorize(self, login: str, is_force_auth: bool = False):
        self.login = login
        is_file_exist = self.data_file_path.exists()

        print(f"is_file_exist: {is_file_exist}")
        yandex_bank_response = {}
        if is_file_exist and not is_force_auth:
            encoded_b64_string = self.data_file_path.read_text()
            encrypted_string = b64decode(encoded_b64_string)
            tag, ciphertext = encrypted_string[:16], encrypted_string[16:]
            decrypted_data = self.get_cipher().decrypt_and_verify(ciphertext, tag)
            cookies = pickle.loads(decrypted_data)
            self.session = requests.Session()
            self.session.cookies.update(cookies)
            print(f"self.session.cookies: {self.session.cookies}")
            yandex_bank_response = (await self._yandex_bank_auth()).json()
        else:
            self.data_dir_path.mkdir(parents=True, exist_ok=True)
            await self._get_cookies()
            await self._auth_start(login)
            await self._auth_submit()
            await self._get_qr_code_for_login()
            await self._check_status_authorize()
            yandex_bank_response = (await self._yandex_bank_auth()).json()
            print(f"else self.session.cookies: {self.session.cookies}")
            self._save_session()

        if yandex_bank_response.get("yandexAuthStatus") == "NEED_RESET":
            await self.authorize(self.login, is_force_auth=True)

    async def _graphql_request(self, domain, operation_name, operation_id, variables=None):
        if variables is None:
            variables = {}
        response: requests.Response = self.session.post(
            url=f"{domain}/graphql?operationId={operation_id}",
            json={
                "operationName": f"{operation_name}",
                "variables": variables,
                "extensions": {
                    "persistedQuery": {
                        "version": 1,
                        "sha256Hash": f"{operation_id}",
                    }
                },
            },
        )

        return response

    async def get_products(self):
        response = await self._graphql_request(self.bank_domain, "HomeProductsV2", "837190662b3bc31125314b8668c184811fe5c1e9ac0425a3544aa12fb45de4f2")

        print("Продукты")
        print(response)
        print(response.text)

        for product in response.json()["data"]["homeProducts"]["products"]:
            self.products.append(
                YandexProduct(
                    id=product["id"],
                    title=product["title"],
                    amount=Decimal(product["value"]["amount"]),
                    currency=product["value"]["currency"],
                )
            )

        return self.products

    async def _start_session_in_ya_bank(self):
        response = await self._graphql_request(self.bank_domain, "startSession", "6431b00e1a7ecee4934e82b7c8c943a53f5c78dbe87eb12bf545dc1d983e4d1c")
        print("_start_session_in_ya_bank")
        print(response.text)
        self.track_id = response.json(
        )["data"]["startSession"]["authorizationTrackId"]

    async def _get_yandex_auth_status(self):
        response = await self._graphql_request(self.bank_domain, "GetYandexAuthStatus", "6e7329fd621c88726c15881846b333fc7ada67ed3e34ea0874a20764fe811831")
        print(response.text)

    async def _otp_auth_ya_bank(self):
        await self._get_yandex_auth_status()
        await self._start_session_in_ya_bank()
        print("запрос кода")
        response = await self._graphql_request(self.bank_domain, "AuthorizationSendCode", "c52d7a8729c4709cce97d7016a77fe057f1e203d3f0f48c3836461dad05742ed", {
            "idempotencyToken": str(uuid.uuid4()),
            "trackId": self.track_id,
        })

        print(response.text)

        print("Введите код")
        code = str(input())

        print("Верификация кода")
        response = await self._graphql_request(self.bank_domain, "AuthorizationVerifyCode", "98ab5299353944d31c5d5640127cbede3b292bdad781fde3f6aeb71982c9dcb6", {
            "code": code, "trackId": self.track_id})

        print(response.text)

    @prepare_response()
    async def get_operations(self, size=1) -> OperationsResponse:
        print("Получений операций")
        response = await self._graphql_request(self.bank_domain, "GetTransactionFeedView", "87390bc3593c2fc82f61213547ce90e4cbae0057448fb8e774c6845efda6dc84", {
            "size": size})

        print("операции")
        # print(response.text)

        return response

    @prepare_response()
    async def get_operation_info(self, id) -> OperationResponse:
        self.session.cookies.set('yandexBankClientTimezone', 'Europe%2FMoscow')

        response = await self._graphql_request(self.bank_domain, "GetOperationV2", "767d5b26e3ab7b544f89e5b5891cd1fafdcaac2268429d809aab9f29a233966c", {
            "id": id})

        return response
