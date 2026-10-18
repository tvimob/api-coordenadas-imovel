import os
import re
from flask import Flask, jsonify, request
from playwright.sync_api import sync_playwright

app = Flask(__name__)


@app.route('/obter-coordenadas', methods=['GET'])
def obter_coordenadas():
  url_imovel = request.args.get('url')

  if not url_imovel:
    print('[LOG] Erro: URL não informada.')
    return jsonify({'sucesso': False, 'erro': 'URL não informada'}), 400

  print(f'[LOG] Iniciando busca de coordenadas para: {url_imovel}')

  try:
    with sync_playwright() as p:
      # Inicia o navegador configurando viewport realista
      browser = p.chromium.launch(headless=True)
      context = browser.new_context(
          user_agent=(
              'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
              ' (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
          ),
          viewport={'width': 1366, 'height': 768},
      )
      page = context.new_page()

      print('[LOG] Navegando para a URL...')
      page.goto(url_imovel, wait_until='domcontentloaded', timeout=60000)

      # 1. Tenta fazer scroll e clicar no botão de mapa
      try:
        print('[LOG] Procurando o botão do mapa (#mapProperty)...')
        map_btn = page.locator('#mapProperty')
        if map_btn.count() > 0:
          map_btn.scroll_into_view_if_needed()
          map_btn.click(force=True)
          print('[LOG] Clique forçado no botão #mapProperty realizado!')
        else:
          print(
              '[LOG] Botão #mapProperty não localizado. Tentando outros'
              ' seletores de mapa...'
          )
          page.evaluate(
              "let el = document.querySelector('#mapProperty') ||"
              " document.querySelector('[data-tab=\"map\"]'); if(el) el.click();"
          )
      except Exception as e:
        print(f'[LOG] Erro/Aviso ao clicar no mapa: {str(e)}')

      # Aguarda a renderização do mapa pelo Mapbox
      print('[LOG] Aguardando 5 segundos para o Mapbox renderizar no DOM...')
      page.wait_for_timeout(5000)

      # 2. Extrai todo o HTML da página após o clique para análise
      html_content = page.content()

      lat = None
      lng = None

      # Busca via Regex direto no HTML capturado (Padrão do link do Mapbox: .../#lng/lat/zoom)
      # Exemplo: apps.mapbox.com/feedback/?...#-49.24246/-16.69721/14
      mapbox_match = re.search(
          r'mapbox\.com/feedback/[^"\']*#(-?\d+\.\d+)/(-?\d+\.\d+)',
          html_content,
      )

      if mapbox_match:
        lng = mapbox_match.group(1)
        lat = mapbox_match.group(2)
        print(
            f'[LOG] Encontrado via Regex no HTML! Longitude: {lng} | Latitude:'
            f' {lat}'
        )

      # 3. Fallback: Procura direto na árvore DOM via JavaScript do Playwright
      if not lat or not lng:
        print('[LOG] Buscando diretamente no DOM do navegador...')
        coords_dom = page.evaluate("""() => {
                    let a = document.querySelector('a.mapbox-improve-map') || 
                            document.querySelector('a[href*="mapbox.com/feedback"]');
                    if (a) {
                        let href = a.getAttribute('href') || '';
                        let m = href.match(/#(-?\\d+\\.\\d+)\\/(-?\\d+\\.\\d+)/);
                        if (m) {
                            return { lng: m[1], lat: m[2] };
                        }
                    }
                    return null;
                }""")
        if coords_dom:
          lng = coords_dom['lng']
          lat = coords_dom['lat']
          print(
              f'[LOG] Encontrado via DOM do navegador! Longitude: {lng} |'
              f' Latitude: {lat}'
          )

      browser.close()

      if not lat or not lng:
        print('[LOG] Erro: Não foi possível capturar as coordenadas.')
        return (
            jsonify({
                'sucesso': False,
                'erro': (
                    'Coordenadas não encontradas no elemento ou no HTML do'
                    ' mapa.'
                ),
            }),
            404,
        )

      print(
          f'[LOG] Sucesso! Retornando coordenadas: Latitude {lat}, Longitude'
          f' {lng}'
      )
      return jsonify({
          'sucesso': True,
          'latitude': lat,
          'longitude': lng,
      })

  except Exception as e:
    print(f'[LOG] Erro de execução: {str(e)}')
    return jsonify({'sucesso': False, 'erro': str(e)}), 500


if __name__ == '__main__':
  app.run(host='0.0.0.0', port=5000)
