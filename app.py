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

      # Clica no botão do mapa para forçar a renderização
      try:
        page.click('#mapProperty', timeout=5000)
        page.wait_for_selector('.gallery-mosaic-container', timeout=5000)
      except Exception:
        pass  # Se demorar ou o botão mudar, continua a leitura

      # Varre a página em busca das coordenadas injetadas pelo Mapbox/Kenlo
      coordenadas = page.evaluate("""() => {
                let lat = null;
                let lng = null;

                // Tenta achar meta tags de localização
                let metaLat = document.querySelector('meta[property="place:location:latitude"], [data-lat]');
                let metaLng = document.querySelector('meta[property="place:location:longitude"], [data-lng]');
                
                if (metaLat) lat = metaLat.content || metaLat.getAttribute('data-lat');
                if (metaLng) lng = metaLng.content || metaLng.getAttribute('data-lng');

                // Se não achar nas metas, varre os scripts da página atrás de variáveis 'lat' e 'lng'
                if (!lat || !lng) {
                    let scripts = Array.from(document.querySelectorAll('script'));
                    for (let s of scripts) {
                        let text = s.innerText;
                        let matchLat = text.match(/["']?lat["']?\s*:\s*(-?\d{1,2}\.\d+)/);
                        let matchLng = text.match(/["']?lng["']?\s*:\s*(-?\d{1,3}\.\d+)/);
                        if (matchLat && matchLng) {
                            lat = matchLat[1];
                            lng = matchLng[1];
                            break;
                        }
                    }
                }

                return { lat: lat, lng: lng };
            }""")

      browser.close()

      return jsonify({
          'sucesso': True,
          'latitude': coordenadas['lat'],
          'longitude': coordenadas['lng'],
      })

  except Exception as e:
    return jsonify({'sucesso': False, 'erro': str(e)}), 500


if __name__ == '__main__':
  app.run(host='0.0.0.0', port=5000)