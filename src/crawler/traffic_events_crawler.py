from typing import Any, Dict, List, Optional
import requests
from bs4 import BeautifulSoup

from crawler.base_crawler import BaseCrawler


class TrafficCrawler(BaseCrawler):
    """
    Crawler específico para extraer información de la etiqueta
    'Ministerio de Transporte (MITRANS)' en Cubadebate.

    Para cada artículo listado en:
      http://www.cubadebate.cu/etiqueta/ministerio-de-transporte-mitrans/
    se extrae:
      - título
      - URL del artículo
      - fecha de publicación
      - un breve párrafo de resumen
    """

    def __init__(
        self,
        retries: int = 3,
        delay: float = 1.0,
    ):

        # 1) Definimos la URL de la etiqueta “MITRANS” en Cubadebate
        base_url = "http://www.cubadebate.cu/etiqueta/ministerio-de-transporte-mitrans/"
        super().__init__(base_url=base_url, retries=retries, delay=delay)

    def crawl(self) -> List[Dict[str, Any]]:
        """
        1. Llama a self.fetch() para descargar el HTML de la página.
        2. Llama a self.parse() para extraer los datos.
        3. Devuelve una lista de diccionarios(hasta ahora) con la info de cada artículo.
        """
        response = self.fetch()

        if not response:
            print("HTML no recuperado")
            return []

        return self.parse(response, False)

    def parse(self, response: requests.Response, filter : bool) -> List[Dict[str, Any]]:
        """
        1. Convierte la respuesta text en un objeto BeautifulSoup.
        2. Busca todos los articulos que representen noticias.
        3. Para cada artículo extrae título, link y fecha.
        4. Extrae el resumen.
        """
        html = response.text
        soup = BeautifulSoup(html, "lxml")

        resultados: List[Dict[str, Any]] = []

        # 1) Encontrar <div> donde se encuentran los articulos
        articulos = soup.find('div', id='archive')

        for art in articulos.find_all('div'):

            print(art.name)  # Testing

            # 2) Extraer el título y la URL del artículo
            h3 = art.find('h3')  # Titulo del articulo
            if not h3:
                continue  

            enlace = h3.find('a')
            if not enlace or not enlace.get('href'):
                continue

            titulo = enlace.get_text(strip=True)
            url = enlace['href'].strip()

            # 3) Extraer fecha de publicación
            time_tag = art.find('div', class_='meta')
            fecha_iso: Optional[str] = None
            if time_tag and time_tag.has_attr('datetime'):
                fecha_iso = time_tag['datetime'].strip()
            else:
                # Si no encontró el atributo “datetime”, podemos intentar leer el texto interno
                fecha_iso = time_tag.get_text(strip=True) if time_tag else None

            # 4) (Opcional) Extraer un snippet / resumen breve
            snippet = None
            excerpt_div = art.find('div', class_='excerpt')
            if excerpt_div:
                # Tomamos el primer <p> interno, si existe
                p = excerpt_div.find('p')
                if p:
                    snippet = p.get_text(strip=True)

            resultados.append({
                "title": titulo,
                "url": url,
                "date": fecha_iso,
                "snippet": snippet,
            })
            print(resultados[0].get("title"))

            if filter :
                self.filter_response(resultados)
                print(resultados[0].get("title"))

        return resultados

    """
    Filtra los articulos que no son de La Habana
    """    
    def filter_response(self, all_articles: List[Dict[str, Any]]):

        for art in all_articles:
            title: str = art.get("title")

            if title.__contains__("La Habana"):
                continue
            else:
                all_articles.remove(art)

        return

