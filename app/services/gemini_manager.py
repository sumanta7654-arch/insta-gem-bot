import time

from google import genai
from google.genai import errors

from app.core.config import (
    GEMINI_API_KEY_1,
    GEMINI_API_KEY_2,
)


gemini_clients = [
    genai.Client(api_key=GEMINI_API_KEY_1),
    genai.Client(api_key=GEMINI_API_KEY_2),
]


class GeminiAPIManager:

    RATE_LIMIT_COOLDOWN = 60
    SERVER_ERROR_COOLDOWN = 30

    def __init__(self, clients):
        self.clients = clients
        self.current_api_index = 0
    
        self.cooldowns = {
            i: 0
            for i in range(len(clients))
        }
    
        self.exhausted = {
            i: False
            for i in range(len(clients))
        }

    def set_cooldown(self, api_index, seconds):
        self.cooldowns[api_index] = time.time() + seconds
    
        print(
            f"Gemini API {api_index + 1} "
            f"cooldown for {seconds} seconds"
        )

    def is_available(self, api_index):
        if self.exhausted[api_index]:
            return False
    
        return time.time() >= self.cooldowns[api_index]

    @property
    def current_client(self):
        return self.clients[self.current_api_index]

    def switch_api(self):
        for _ in range(len(self.clients)):
            self.current_api_index = (
                self.current_api_index + 1
            ) % len(self.clients)
    
            if self.is_available(self.current_api_index):
                print(
                    f"Switched to Gemini API "
                    f"{self.current_api_index + 1}"
                )
                return True

        return False

    def classify_error(self, error: errors.APIError) -> str:
        error_code = None

        if isinstance(error.details, dict):
            error_data = error.details.get("error", {})
            error_code = error_data.get("code")

        if error_code == "quota_exceeded":
            return "quota_exceeded"

        if error_code in (
            "rate_limit_exceeded",
            "too_many_requests",
        ):
            return "rate_limit"

        if error.code in (500, 502, 503, 504):
            return "server_error"

        if error.code in (400, 401, 403, 404):
            return "client_error"

        return "unknown"

    def execute(self, request_func):
        failed_api = self.current_api_index
    
        try:
            return request_func(self.current_client)
    
        except errors.APIError as e:
            error_type = self.classify_error(e)
    
            print(
                f"Gemini API {failed_api + 1} "
                f"error: {error_type}"
            )
    
            if error_type == "quota_exceeded":
                self.exhausted[failed_api] = True
    
            elif error_type == "rate_limit":
                self.set_cooldown(
                    failed_api,
                    self.RATE_LIMIT_COOLDOWN
                )
    
            elif error_type == "server_error":
                self.set_cooldown(
                    failed_api,
                    self.SERVER_ERROR_COOLDOWN
                )
    
            else:
                raise
    
            # Try another available API
            if not self.switch_api():
                raise
    
            backup_api = self.current_api_index
    
            try:
                return request_func(self.current_client)
    
            except errors.APIError as backup_error:
                backup_error_type = self.classify_error(
                    backup_error
                )
    
                print(
                    f"Gemini API {backup_api + 1} "
                    f"error: {backup_error_type}"
                )
    
                if backup_error_type == "quota_exceeded":
                    self.exhausted[backup_api] = True
    
                elif backup_error_type == "rate_limit":
                    self.set_cooldown(
                        backup_api,
                        self.RATE_LIMIT_COOLDOWN
                    )
    
                elif backup_error_type == "server_error":
                    self.set_cooldown(
                        backup_api,
                        self.SERVER_ERROR_COOLDOWN
                    )
    
                raise

gemini_manager = GeminiAPIManager(gemini_clients)