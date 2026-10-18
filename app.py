import os
from flask import Flask, jsonify, request
from playwright.sync_api import sync_playwright

app = Flask(__name__)


@app.route('/obter-coordenadas', methods=['GET'])
def obter_coordenadas():
  url_imovel = request.args.get('url')

  if not url_imovel:
    return jsonify({'sucesso': False, 'erro': 'URL não informada'}), 400

  try:
    with sync_playwright() as p:
      # Inicia o navegador invisível
      browser = p.chromium.launch(headless=True)
      page = browser.new_page()

      # Acessa a página do imóvel
      page.goto(url_imovel, timeout=60000)

      # Clica no botão do mapa (#mapProperty) para forçar o Mapbox a carregar os elementos
      try:
        page.click('#mapProperty', timeout=5000)
        # Aguarda o container do mosaico ou o link do Mapbox aparecer
        page.wait_for_selector(
            '.gallery-mosaic-container, .mapbox-improve-map', timeout=8000
        )
      except Exception:
        pass  # Continua mesmo se o clique falhar ou demorar

      # Executa o script no navegador para extrair as coordenadas do link do Mapbox
      coordenadas = page.evaluate("""() => {
                let lat = null;
                let lng = null;

                // Procura especificamente pelo link do Mapbox que contém as coordenadas (ex: #/lng/lat/zoom)
                let improveMapLink = document.querySelector('a.mapbox-improve-map');
                if (improveMapLink) {
                    let href = improveMapLink.getAttribute('href');
                    // Exemplo de href: .../#-49.24246/-16.69721/14
                    let match = href && href.match(/#(-?\\d+\\.\\d+)\\/(-?\\d+\\.\\d+)/);
                    if (match) {
                        lng = match[1]; // Longitude vem primeiro no padrão do Mapbox
                        lat = match[2]; // Latitude vem em segundo
                    }
                }

                // Plano B: Se não achar no link, tenta varrer qualquer atributo ou texto com o padrão de coordenadas do mapa
                if (!lat || !lng) {
                    let allLinks = Array.from(document.querySelectorAll('a'));
                    for (let a of allLinks) {
                        let h = a.getAttribute('href') || '';
                        let m = h.match(/#(-?\\d+\\.\\d+)\\/(-?\\d+\\.\\d+)/);
                        if (m) {
                            lng = m[1];
                            lat = m[2];
                            break;
                        }
                    }
                }

                return { lat: lat, lng: lng };
            }""")

      browser.close()

      if not coordenadas['lat'] or not coordenadas['lng']:
        return (
            jsonify({
                'sucesso': False,
                'erro': 'Coordenadas não encontradas no mapa',
            }),
            404,
        )

      return jsonify({
          'sucesso': True,
          'latitude': coordenadas['lat'],
          'longitude': coordenadas['lng'],
      })

  except Exception as e:
    return jsonify({'sucesso': False, 'erro': str(e)}), 500


if __name__ == '__main__':
  app.run(host='0.0.0.0', port=5000)

// Atualizado 1
