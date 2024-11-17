# custom_components/omada_direct/omada_client.py

import asyncio
import hashlib
import logging
import ssl
import types  # Import types module for SimpleNamespace
from typing import Optional

import aiohttp
from aiohttp import ClientConnectorError, ClientSession


# Define custom exceptions for clarity
class OmadaClientError(Exception):
    """Base exception for OmadaClient."""


class LoginError(OmadaClientError):
    """Raised when login fails due to invalid credentials or other issues."""


class FetchDataError(OmadaClientError):
    """Raised when fetching data fails."""


class LogoutError(OmadaClientError):
    """Raised when logout fails."""


class OmadaClient:
    """A minimal asynchronous client library for TP-Link Omada EAP.

    Attributes:
        host (str): The base URL of the Omada EAP (e.g., 'https://10.42.99.62').
        username (str): Username for login.
        password (str): Password for login.
        ssl_verify (bool): Whether to verify SSL certificates.
        logger (logging.Logger): Logger instance for logging.
    """

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        ssl_verify: bool = False,
        logger: Optional[logging.Logger] = None,
    ):
        """Initializes the OmadaClient.

        Args:
            host (str): Base URL of the Omada EAP.
            username (str): Username for login.
            password (str): Password for login.
            ssl_verify (bool, optional): Whether to verify SSL certificates. Defaults to False.
            logger (logging.Logger, optional): Custom logger. If None, a default logger is created.
        """
        self.host = host.rstrip("/")
        self.username = username
        self.password = password
        self.ssl_verify = ssl_verify

        # Configure logger
        if logger is None:
            self.logger = logging.getLogger(__name__)
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        else:
            self.logger = logger

        # Initialize other attributes
        self.session: Optional[ClientSession] = None
        self.logged_in = False

    async def __aenter__(self):
        """Enter the asynchronous context manager."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the asynchronous context manager."""
        await self.close()

    async def connect(self):
        """Establishes an aiohttp ClientSession with appropriate configurations."""
        self.logger.debug("Establishing HTTP session with Omada EAP.")

        # Create SSL context
        ssl_context = ssl.create_default_context()
        if not self.ssl_verify:
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            ssl_context.options &= ~ssl.OP_NO_TLSv1_2  # Ensure TLSv1.2 is enabled
            ssl_context.set_ciphers("AES256-GCM-SHA384")

        # Initialize CookieJar with unsafe=True to accept host-only cookies
        jar = aiohttp.CookieJar(unsafe=True)

        # Define TraceConfig for detailed logging if needed
        trace_config = aiohttp.TraceConfig()
        trace_config.on_request_start.append(self._on_request_start)
        trace_config.on_request_end.append(self._on_request_end)
        trace_config.on_response_chunk_received.append(self._on_response_chunk_received)

        try:
            self.session = aiohttp.ClientSession(
                headers=self._default_headers(),
                cookie_jar=jar,
                connector=aiohttp.TCPConnector(ssl=ssl_context),
                trace_configs=[trace_config],
            )
            self.logger.debug("HTTP session established successfully.")
        except Exception as e:
            self.logger.error(f"Failed to establish HTTP session: {e}")
            raise OmadaClientError(f"Failed to establish HTTP session: {e}") from e

    async def close(self):
        """Closes the aiohttp ClientSession."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.logger.debug("HTTP session closed.")

    def _default_headers(self) -> dict:
        """Returns the default headers for HTTP requests.

        Returns:
            dict: Default HTTP headers.
        """
        return {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": self.host,
            "Referer": f"{self.host}/logout.html",
        }

    # Trace callback methods for detailed logging
    async def _on_request_start(self, session, trace_config_ctx, params):
        self.logger.debug("=== Request Start ===")
        self.logger.debug(f"Method: {params.method}")
        self.logger.debug(f"URL: {params.url}")
        self.logger.debug(f"Headers: {dict(params.headers)}")
        if params.method.upper() in ["POST", "PUT", "PATCH"]:
            # Access the request body from trace_config_ctx
            data = getattr(trace_config_ctx, "data", None)
            if data:
                # Mask sensitive information
                masked_data = {
                    k: ("****" if k.lower() == "password" else v)
                    for k, v in data.items()
                }
                self.logger.debug(f"Request Body: {masked_data}")

    async def _on_request_end(self, session, trace_config_ctx, params):
        self.logger.debug("=== Request End ===")
        self.logger.debug(f"URL: {params.url}")
        self.logger.debug(f"Status: {params.response.status}")
        self.logger.debug(f"Response Headers: {dict(params.response.headers)}")

    async def _on_response_chunk_received(self, session, trace_config_ctx, params):
        # Optional: Implement if you need to log response chunks
        pass

    async def login(self):
        """Logs into the Omada EAP.

        Raises:
            LoginError: If login fails due to invalid credentials or other issues.
        """
        await self.ensure_authenticated()

    async def ensure_authenticated(self):
        """Ensures that the client is authenticated. Logs in if not already authenticated.

        Raises:
            LoginError: If login fails or JSESSIONID cookie is missing/invalid.
        """
        if self.logged_in:
            self.logger.debug("Already authenticated.")
            return

        if not self.session:
            self.logger.debug("No active session. Establishing a new session.")
            await self.connect()

        login_url = f"{self.host}/"
        payload = {
            "username": self.username,
            "password": hashlib.md5(self.password.encode()).hexdigest().upper(),
        }

        try:
            self.logger.info("Attempting to log in to Omada EAP.")
            async with self.session.post(
                login_url,
                data=payload,
                trace_request_ctx=types.SimpleNamespace(data=payload),
            ) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    if (
                        "success" in text.lower()
                        or resp.headers.get("Content-Length") == "0"
                    ):
                        # Retrieve cookies associated with the login URL
                        cookies = self.session.cookie_jar.filter_cookies(login_url)
                        jsessionid_cookie = cookies.get("JSESSIONID")

                        if jsessionid_cookie and jsessionid_cookie.value:
                            self.logged_in = True
                            self.logger.info(
                                "Login successful. JSESSIONID cookie is present and valid."
                            )
                        else:
                            self.logger.error(
                                "Login failed: JSESSIONID cookie missing or invalid."
                            )
                            raise LoginError(
                                "Login failed: JSESSIONID cookie missing or invalid."
                            )
                    else:
                        self.logger.error("Login failed: Unexpected response content.")
                        raise LoginError("Login failed: Unexpected response content.")
                elif resp.status == 401:
                    self.logger.error(
                        "Login failed: Unauthorized (401). Check your credentials."
                    )
                    raise LoginError(
                        "Login failed: Unauthorized (401). Check your credentials."
                    )
                else:
                    self.logger.error(f"Login failed with status code {resp.status}.")
                    raise LoginError(f"Login failed with status code {resp.status}.")
        except ClientConnectorError as e:
            self.logger.error(f"Connection error during login: {e}")
            raise LoginError(f"Connection error during login: {e}") from e
        except asyncio.TimeoutError:
            self.logger.error("Login request timed out.")
            raise LoginError("Login request timed out.")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during login: {e}")
            raise LoginError(f"An unexpected error occurred during login: {e}") from e

    async def fetch_clients(self) -> dict:
        """Fetches data from the Omada EAP.

        Args:
            operation (str, optional): Operation type. Defaults to 'load'.

        Returns:
            dict: Parsed JSON data from the response.

        Raises:
            FetchDataError: If fetching data fails.
        """
        try:
            await self.ensure_authenticated()
        except LoginError as e:
            self.logger.error(f"Cannot fetch data because authentication failed: {e}")
            raise FetchDataError(f"Authentication failed: {e}") from e

        data_url = f"{self.host}/data/status.client.user.json"
        params = {"operation": "load"}

        try:
            self.logger.info("Fetching data from Omada EAP.")
            async with self.session.get(data_url, params=params) as resp:
                if resp.status == 200:
                    try:
                        data = await resp.json(content_type=None)
                        self.logger.debug(f"Fetched Data: {data}")
                        self.logger.info("Data fetched successfully.")
                        return data
                    except Exception as e:
                        self.logger.error(f"Failed to parse JSON response: {e}")
                        raise FetchDataError(
                            f"Failed to parse JSON response: {e}"
                        ) from e
                else:
                    self.logger.error(
                        f"Failed to fetch data with status code {resp.status}."
                    )
                    body = await resp.text()
                    self.logger.debug(f"Response Body: {body}")
                    raise FetchDataError(
                        f"Failed to fetch data with status code {resp.status}."
                    )
        except ClientConnectorError as e:
            self.logger.error(f"Connection error while fetching data: {e}")
            raise FetchDataError(f"Connection error while fetching data: {e}") from e
        except asyncio.TimeoutError:
            self.logger.error("Data fetch request timed out.")
            raise FetchDataError("Data fetch request timed out.")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred while fetching data: {e}")
            raise FetchDataError(
                f"An unexpected error occurred while fetching data: {e}"
            ) from e

    async def fetch_device_info(self) -> dict:
        """Fetches device information from the Omada EAP.

        Returns:
            dict: Parsed JSON data from the response.

        Raises:
            FetchDataError: If fetching device info fails.
        """
        device_info_url = f"{self.host}/data/status.device.json"
        params = {"operation": "read"}

        try:
            self.logger.info("Fetching device information from Omada EAP.")
            async with self.session.get(device_info_url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    self.logger.debug(f"Device Info Data: {data}")
                    return data
                else:
                    self.logger.error(
                        f"Failed to fetch device info with status code {resp.status}."
                    )
                    body = await resp.text()
                    self.logger.debug(f"Response Body: {body}")
                    raise FetchDataError(
                        f"Failed to fetch device info with status code {resp.status}."
                    )
        except Exception as e:
            self.logger.error(f"An error occurred while fetching device info: {e}")
            raise FetchDataError(
                f"An error occurred while fetching device info: {e}"
            ) from e

    async def logout(self):
        """Logs out from the Omada EAP.

        Raises:
            LogoutError: If logout fails.
        """
        if not self.session or not self.logged_in:
            self.logger.warning("Not logged in. Skipping logout.")
            return

        logout_url = f"{self.host}/logout.html"

        try:
            self.logger.info("Logging out from Omada EAP.")
            async with self.session.get(logout_url) as resp:
                if resp.status == 200:
                    self.logged_in = False
                    self.logger.info("Logged out successfully.")
                else:
                    self.logger.error(f"Logout failed with status code {resp.status}.")
                    body = await resp.text()
                    self.logger.debug(f"Response Body: {body}")
                    raise LogoutError(f"Logout failed with status code {resp.status}.")
        except ClientConnectorError as e:
            self.logger.error(f"Connection error during logout: {e}")
            raise LogoutError(f"Connection error during logout: {e}") from e
        except asyncio.TimeoutError:
            self.logger.error("Logout request timed out.")
            raise LogoutError("Logout request timed out.")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during logout: {e}")
            raise LogoutError(f"An unexpected error occurred during logout: {e}") from e
