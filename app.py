import os
from flask import Flask, jsonify, request
from playwright.sync_api import sync_playwright

app = Flask(__name__)


@app.route('/obter-coordenadas', methods=['GET'])
def obter_coordenadas():
  url_imovel = request.args.get('url')

  if not url_imovel:
    print('[LOG] Erro: URL não informada.')
    return jsonify({'sucesso': False, 'erro': 'URL não informada'}), 400

  print(f'[LOG] Iniciando scraping para a URL: {url_imovel}')

  try:
    with sync_playwright() as p:
      print('[LOG] Abrindo navegador headless...')
      browser = p.chromium.launch(headless=True)
      page = browser.new_page()

      print('[LOG] Acessando página do imóvel...')
      page.goto(url_imovel, timeout=60000)

      print('[LOG] Tentando clicar no botão do mapa (#mapProperty)...')
      try:
        page.click('#mapProperty', timeout=5000)
        print(
            '[LOG] Clique realizado com sucesso! Aguardando o mapa carregar...'
        )
        # Aguarda 4 segundos fixos para o Mapbox renderizar os componentes visuais e o link de feedback
        page.wait_for_timeout(4000)
      except Exception as e:
        print(f'[LOG] Aviso no clique ou espera do mapa: {str(e)}')

      print('[LOG] Buscando elemento a.mapbox-improve-map na página...')
      coordenadas = page.evaluate("""() => {
                let lat = null;
                let lng = null;

                // Procura especificamente na tag solicitada
                let improveMapLink = document.querySelector('a.mapbox-improve-map');
                if (improveMapLink) {
                    let href = improveMapLink.getAttribute('href');
                    console.log('Link encontrado:', href);
                    
                    // Exemplo de href: .../#-49.24246/-16.69721/14
                    let match = href && href.match(/#(-?\\d+\\.\\d+)\\/(-?\\d+\\.\\d+)/);
                    if (match) {
                        lng = match[1]; // Longitude
                        lat = match[2]; // Latitude
                    }
                } else {
                    console.log('Elemento a.mapbox-improve-map NÃO foi encontrado no DOM.');
                }

                return { lat: lat, lng: lng };
            }""")

      browser.close()

      print(f"[LOG] Resultado obtido -> Lat: {coordenadas['lat']} | Lng: {coordenadas['lng']}")

      if not coordenadas['lat'] or not coordenadas['lng']:
        print('[LOG] Falha: Coordenadas retornaram vazias.')
        return (
            jsonify({
                'sucesso': False,
                'erro': (
                    'Coordenadas não encontradas na tag a.mapbox-improve-map'
                ),
            }),
            404,
        )

      return jsonify({
          'sucesso': True,
          'latitude': coordenadas['lat'],
          'longitude': coordenadas['lng'],
      })

  except Exception as e:
    print(f'[LOG] Erro crítico na execução: {str(e)}')
    return jsonify({'sucesso': False, 'erro': str(e)}), 500


if __name__ == '__main__':
  app.run(host='0.0.0.0', port=5000)
