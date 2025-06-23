from typing import Any, Dict, List, Optional
import requests
from bs4 import BeautifulSoup
import re
from unidecode import unidecode

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

        return self.parse(response, True)

    def parse(self, response: requests.Response, filtrar : bool) -> List[Dict[str, Any]]:
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
            title_section = art.find('div', class_='title')  # Titulo del articulo
            if not title_section:
                continue  

            enlace = title_section.find('a')
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

            if filtrar :
                self.filter_response(resultados)
                print(resultados[0].get("title"))

        return resultados
    
    CLOSURE_KW  = ["cierre", "cerrar", "cerrará", "cerrarán",
               "cortará", "cortarán", "interrupción", "desvío",
               "desviarán", "reparación", "obras", "mantenimiento"]

    HABANA_KW   = ["la habana", "habana",
                "centro habana", "habana vieja", "plaza de la revolución",
                "playa", "regla", "guanabacoa", "10 de octubre",
                "cerro", "arroyo naranjo", "boyeros", "cotorro",
                "san miguel del padrón", "habana del este"]
    
    @staticmethod
    def _norm(text: str) -> str:
        """Minúsculas sin tildes para comparación robusta."""
        return unidecode(text.lower())
    
    # Palabras que suelen preceder al nombre de la vía
    _VIA_PREFIXES = r"(?:calle|avenida|ave\.?|carretera|autopista|via)"
    # Ejemplo de nombre de vía → “23”, “Primera”, “Infanta”, “Vía Blanca”, “26 de Julio”
    _VIA_NAME     = r"[A-ZÁÉÍÓÚÑ0-9][A-Za-zÁÉÍÓÚÑ0-9\s°\-]{1,40}"

    VIA_REGEX = re.compile(
        rf"\b{_VIA_PREFIXES}\s+{_VIA_NAME}", flags=re.IGNORECASE)
    
    def _descarga_cuerpo(self, url: str) -> str | None:
        """Devuelve texto plano del artículo (máx. ~8 KB) o None."""
        resp = self.fetch(url=url)
        if not resp:
            return None
        soup = BeautifulSoup(resp.text, "lxml")
        # En Cubadebate el cuerpo suele estar dentro de <div class="entry-content">
        cont = soup.find("div", class_="entry-content")
        if not cont:
            cont = soup  # fallback: usar todo
        # get_text(" ") conserva espacios; recorta para no cargar memoria
        return cont.get_text(" ", strip=True)[:8000]

    def _extrae_vias(self, texto_html: str) -> List[str]:
        """Busca coincidencias con VIA_REGEX, devuelve lista única normalizada."""
        matches = self.VIA_REGEX.findall(texto_html)
        # Normalizamos: quitamos dobles espacios y capitalizamos cada palabra
        calles = {re.sub(r"\s+", " ", m.strip()).title() for m in matches}
        return sorted(calles)
    
    def filter_response(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        1. Prefiltra por (keyword de La Habana) ∧ (keyword de cierre) en título+snippet.
        2. Para cada pre-candidato:
        - Descarga el cuerpo y confirma que hay keyword de cierre.
        - Extrae nombres de vías.
        3. Devuelve lista filtrada (cada dict con clave 'streets').
        """
        # -------- Paso A : prefiltrado rápido por título/snippet ----------
        prelim = []
        for art in articles:
            texto = self._norm(f"{art['title']} {art.get('snippet', '')}")
            if (any(k in texto for k in self.HABANA_KW)
                    and any(k in texto for k in self.CLOSURE_KW)):
                print(f"✅ Candidato detectado: {art['title']}")
                prelim.append(art)
            else:
                print(f"❌ Ignorado: {art['title']}")    

        # -------- Paso B : verificación y extracción de vías -------------
        finales = []
        for art in prelim:
            print(f"🔎 Verificando artículo: {art['url']}")
            cuerpo = self._descarga_cuerpo(art["url"])
            if not cuerpo:
                print("   ⚠️ No se pudo obtener el cuerpo del artículo.")
                continue

            cuerpo_norm = self._norm(cuerpo)
            if not any(k in cuerpo_norm for k in self.CLOSURE_KW):
                print("   🚫 No se detectan palabras clave de cierre en el texto completo.")
                # No se confirma el cierre en el texto completo
                continue

            calles = self._extrae_vias(cuerpo)
            if not calles:
                print("   🚧 No se encontraron nombres de vías.")
                # No se mencionan vías concretas; puedes decidir si descartas
                continue
            print(f"   ✅ Vías detectadas: {', '.join(calles)}")

            # Añadimos la lista de calles encontradas y guardamos
            art = art.copy()         # evitamos mutar el original
            art["streets"] = calles
            finales.append(art)

        return finales
