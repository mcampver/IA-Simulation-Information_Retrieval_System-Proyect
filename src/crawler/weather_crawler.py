from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

try:
    import aiohttp
except ModuleNotFoundError:  # pragma: no cover
    aiohttp = None          # Nos permitirá detectar si existe o no

from crawler.base_crawler import BaseCrawler


class OpenMeteoCrawler(BaseCrawler):
    """
    Crawler que utiliza la API pública de Open-Meteo para obtener:
      • Probabilidad de lluvia y velocidad del viento (pronóstico horario y diario).
      • Clima actual (métodos sync y async).
    """

    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(
        self,
        lat: float,
        lon: float,
        retries: int = 3,
        delay: float = 1.0,
    ):
        """
        :param lat: Latitud del punto geográfico
        :param lon: Longitud del punto geográfico
        :param retries: Número de reintentos en caso de error de red
        :param delay: Pausa entre reintentos
        """
        self.lat = lat
        self.lon = lon

        super().__init__(base_url=self.BASE_URL, retries=retries, delay=delay)

    # ---------------------------------------------------------------------
    # 1) PRONÓSTICO HORARIO Y DIARIO (ya existente)
    # ---------------------------------------------------------------------
    def crawl(self) -> Dict[str, Any]:
        """Devuelve dict con hourly_today y daily_forecast (5 días)."""
        params = {
            "latitude": self.lat,
            "longitude": self.lon,
            "hourly": "precipitation_probability,wind_speed_10m",
            "daily": "precipitation_probability_max,wind_speed_10m_max",
            "timezone": "auto",
        }

        response = self.fetch(params=params)
        if not response:
            return {}

        return self.parse(response)

    def parse(self, response: requests.Response) -> Dict[str, Any]:
        data = response.json()

        # --- Datos horarios (solo para hoy) -----------------------------
        hourly: List[Dict[str, Any]] = []
        if "hourly" in data:
            for t, rain, wind in zip(
                data["hourly"]["time"],
                data["hourly"]["precipitation_probability"],
                data["hourly"]["wind_speed_10m"],
            ):
                if self._is_today(t):
                    hourly.append(
                        {"time": t, "rain_probability": rain, "wind_speed": wind}
                    )

        # --- Datos diarios (siguientes 5 días) --------------------------
        daily: List[Dict[str, Any]] = []
        if "daily" in data:
            for date, rain, wind in zip(
                data["daily"]["time"][:5],
                data["daily"]["precipitation_probability_max"][:5],
                data["daily"]["wind_speed_10m_max"][:5],
            ):
                daily.append(
                    {
                        "date": date,
                        "rain_probability_max": rain,
                        "wind_speed_max": wind,
                    }
                )

        return {
            "coordinates": {"lat": self.lat, "lon": self.lon},
            "hourly_today": hourly,
            "daily_forecast": daily,
        }

    @staticmethod
    def _is_today(iso_datetime: str) -> bool:
        """Devuelve True si iso_datetime pertenece a la fecha actual."""
        return iso_datetime.split("T")[0] == datetime.now().date().isoformat()

    # ---------------------------------------------------------------------
    # 2) CLIMA ACTUAL – VERSIÓN ASÍNCRONA
    # ---------------------------------------------------------------------
    async def get_current_weather_async(self) -> Optional[Dict[str, Any]]:
        """
        Devuelve un dict con los valores 'current' de Open-Meteo usando aiohttp.
        Retorna None si hay error o si aiohttp no está instalado.
        """
        if aiohttp is None:
            print("aiohttp no disponible: usa get_current_weather_sync()")
            return None

        params = {
            "latitude": self.lat,
            "longitude": self.lon,
            # Lista de variables que queremos del bloque 'current'
            "current": ",".join(
                [
                    "temperature_2m",
                    "precipitation",
                    "wind_speed_10m",
                    "cloud_cover",
                    "weather_code",
                    "visibility",
                ]
            ),
            "timezone": "America/Havana",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.BASE_URL, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("current", {})
                    print(f"Error Open-Meteo (async): {resp.status}")
        except Exception as exc:  # pragma: no cover
            print(f"Excepción en get_current_weather_async: {exc}")

        return None

    # ---------------------------------------------------------------------
    # 3) CLIMA ACTUAL – VERSIÓN SINCRÓNICA
    # ---------------------------------------------------------------------
    def get_current_weather_sync(self) -> Optional[Dict[str, Any]]:
        """
        Igual que la versión async, pero con requests.
        Pensado para scripts o entornos donde no se use asyncio.
        """
        params = {
            "latitude": self.lat,
            "longitude": self.lon,
            "current": ",".join(
                [
                    "temperature_2m",
                    "precipitation",
                    "wind_speed_10m",
                    "cloud_cover",
                    "weather_code",
                    "visibility",
                ]
            ),
            "timezone": "America/Havana",
        }

        try:
            resp = requests.get(self.BASE_URL, params=params, timeout=10)
            if resp.status_code == 200:
                return resp.json().get("current", {})
            print(f"Error Open-Meteo (sync): {resp.status_code}")
        except Exception as exc:  # pragma: no cover
            print(f"Excepción en get_current_weather_sync: {exc}")

        return None
