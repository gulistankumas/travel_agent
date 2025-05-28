from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import os
import openai

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('chat.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    state = data.get('state', {})
    user_message = data.get('message', '').strip()
    response = ''
    next_state = state.copy()

    # Step 1: If no state, ask for summary
    if not state:
        response = "Tatil planını kısaca anlat (örn: Mayısta arkadaşlarımla sakin bir doğa tatili istiyorum):"
        next_state['step'] = 'summary'
    elif state.get('step') == 'summary':
        next_state['user_input'] = user_message
        response = "Kaç günlük bir tatil planlıyorsun? (örn: 4):"
        next_state['step'] = 'days'
    elif state.get('step') == 'days':
        try:
            gun_sayisi = int(user_message)
        except ValueError:
            gun_sayisi = 4
        next_state['gun_sayisi'] = gun_sayisi
        # Analyze preferences
        analiz_prompt = f"""
Aşağıdaki kullanıcı girdisine göre seyahat tercihlerini belirle. Süre olarak {gun_sayisi} gün olduğunu varsay:

Kullanıcı Girdisi: {next_state['user_input']}

Sonuçları şu formatta ver:
Tatil türü: ...\nSüre: {gun_sayisi} gün\nMevsim: ...\nBölge: ...\n"""
        analiz_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": analiz_prompt}],
            temperature=0.5,
            max_tokens=200
        )
        analiz_text = analiz_response['choices'][0]['message']['content'].strip()
        next_state['analiz_text'] = analiz_text
        # Suggest regions
        bolge_sec_prompt = f"""
Kullanıcının tatil tercihleri:
{analiz_text}

Bu bilgilere göre 5 önerilen bölge ver. Her birini 1 cümleyle tanıt. Kullanıcıya \"Hangisini tercih edersin?\" diye sor.
"""
        bolge_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": bolge_sec_prompt}],
            temperature=0.7,
            max_tokens=400
        )
        bolge_onerileri = bolge_response['choices'][0]['message']['content'].strip()
        next_state['bolge_onerileri'] = bolge_onerileri
        response = f"📌 Önerilen Bölgeler:\n{bolge_onerileri}\n\nHangi bölgeyi istersin? Lütfen adını yaz:"
        next_state['step'] = 'region'
    elif state.get('step') == 'region':
        next_state['secilen_bolge'] = user_message
        gun_sayisi = next_state.get('gun_sayisi', 4)
        analiz_text = next_state.get('analiz_text', '')
        secilen_bolge = user_message
        planlama_prompt = f"""
Kullanıcının seyahat tercihleri şunlardır:
{analiz_text}

Seçilen bölge veya bölgeler: {secilen_bolge}

Bu bilgilere göre {gun_sayisi} günlük detaylı bir seyahat planı oluştur.
Her gün için şunları içersin:
- Gün başlığı
- Gezilecek yerler
- Yerel deneyimler
- Ulaşım/konaklama önerileri
- Günlük aktivite önerileri

Yanıt dili: Türkçe
"""
        plan_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": planlama_prompt}],
            temperature=0.7,
            max_tokens=min(1500, gun_sayisi * 300)
        )
        plan = plan_response['choices'][0]['message']['content'].strip()
        response = f"🗺️ Seyahat Planın Hazır:\n{plan}"
        next_state['step'] = 'done'
    else:
        response = "Yeni bir plan için sayfayı yenileyin."
    return jsonify({"response": response, "state": next_state})

if __name__ == "__main__":
    app.run(debug=True)
