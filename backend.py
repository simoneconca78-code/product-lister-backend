from flask import Flask, request, jsonify
import anthropic
import requests
import json
import base64
import os

app = Flask(__name__)

# API Keys
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")
AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN", "")
AIRTABLE_BASE = "appJ47ZDJ3pJIfYRK"
AIRTABLE_TABLE = "Annunci"

client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

@app.route('/api/generate-listing', methods=['POST'])
def generate_listing():
    try:
        data = request.json
        image_base64 = data.get('image')
        user_text = data.get('text', '')
        
        if not image_base64:
            return jsonify({'error': 'No image provided'}), 400
        
        if ',' in image_base64:
            image_base64 = image_base64.split(',')[1]
        
        vision_response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_base64
                        }
                    },
                    {
                        "type": "text",
                        "text": "Descrivi brevemente questo prodotto usato. Includi: tipo, colore, materiale, condizione, dimensioni, difetti visibili. Rispondi in italiano, max 200 parole."
                    }
                ]
            }]
        )
        
        analysis_text = vision_response.content[0].text
        
        prompt = f"""Sei un esperto di annunci per prodotti usati (Subito, Vinted, Wallapop) in Italia.

ANALISI FOTO:
{analysis_text}

TESTO UTENTE AGGIUNTIVO:
{user_text if user_text else '(nessuno)'}

GENERA UN JSON VALIDO (solo JSON, niente altro):
{{
  "titolo": "massimo 80 caratteri, accattivante e chiaro",
  "descrizione": "200-300 caratteri, dettagliata e persuasiva",
  "categoria": "Zaino|Accessori|Abbigliamento|Elettronica|Arredamento|Sport|Altro",
  "condizione": "Buone|Buone condizioni|Da restaurare|Usato|Ottimo",
  "prezzo": 45
}}

REGOLE:
- Prezzo realistico basato su foto e descrizione
- Italiano naturale
- Solo JSON nel responso, niente testo aggiuntivo
"""
        
        text_response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=400,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        
        json_text = text_response.content[0].text
        listing = json.loads(json_text)
        
        airtable_url = f"https://api.airtable.com/v0/{AIRTABLE_BASE}/{AIRTABLE_TABLE}"
        headers = {
            "Authorization": f"Bearer {AIRTABLE_TOKEN}",
            "Content-Type": "application/json"
        }
        
        airtable_data = {
            "records": [{
                "fields": {
                    "Titolo": listing.get('titolo', ''),
                    "Descrizione": listing.get('descrizione', ''),
                    "Categoria": listing.get('categoria', ''),
                    "Prezzo": listing.get('prezzo', 0),
                    "Condizione": listing.get('condizione', ''),
                    "Stato": listing.get('condizione', '')
                }
            }]
        }
        
        airtable_response = requests.post(airtable_url, headers=headers, json=airtable_data)
        
        if airtable_response.status_code != 200:
            return jsonify({'error': 'Airtable save failed'}), 500
        
        record_id = airtable_response.json()['records'][0]['id']
        
        return jsonify({
            'success': True,
            'listing': listing,
            'record_id': record_id,
            'analysis': analysis_text
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
