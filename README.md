# Stone Age Athlete — Video Stüdyosu

Senaryodan YouTube videosuna giden üretim hattı: **senaryo → görsel planı → seslendirme → zamanlama → görseller → kurgu**.
Her aşama değiştirilebilir bir parça. Başlangıçta hepsi **ücretsiz** çalışır; iş büyüdüğünde `config.yaml`'da
tek satır değiştirip ücretli servise geçersin, kod değişmez.

| Aşama | Ücretsiz (varsayılan) | Ücretli (hazır, tek satırla açılır) |
| --- | --- | --- |
| Görsel planı | `planner.provider: manual` — Claude sohbetinde | `anthropic` — Anthropic API, otomatik |
| Seslendirme | `tts.provider: kokoro` — bilgisayarında çalışır | `elevenlabs` — daha doğal ses, kelime-kelime zamanlama |
| Görseller | `images.default_engine: svg` — kodla çizim | `gemini` — Nano Banana AI görselleri (shot bazında da seçilebilir) |
| Kurgu | FFmpeg | — |

## Kurulum (bir kez)

Gerekenler: **Python 3.10+**, **FFmpeg**, **Git**.

- Windows: `winget install Python.Python.3.12 Gyan.FFmpeg Git.Git` (sonra terminali kapatıp aç)
- Mac: `brew install python ffmpeg git`

```bash
git clone https://github.com/tosunbeytullah9-ui/stone-age-athlete.git
cd stone-age-athlete
python -m venv .venv
# Windows:  .venv\Scripts\activate      Mac/Linux:  source .venv/bin/activate
pip install -r requirements.txt -r requirements-voice.txt
python -m playwright install chromium
copy .env.example .env        # Mac/Linux: cp .env.example .env   (anahtarlar sadece ücretli servisler için)
```

İlk seslendirmede Kokoro ses modeli (~350 MB) `models/` klasörüne kendiliğinden iner.

Kurulumu denemek için: `python -m studio all 001-tougher-than-athletes` → `projects/001-tougher-than-athletes/build/video.mp4`

## Yeni video üretmek

```bash
python -m studio new 002-born-to-run --title "Were Humans Really Born to Run?"
```

1. **Senaryo:** `projects/002-born-to-run/script.md` dosyasına İngilizce anlatım metnini yaz. Paragrafları boş satırla ayır.
   `#` ile başlayan satırlar okunmaz. Kaynakları `sources.md` içine not et.
2. **Böl:** `python -m studio split 002-born-to-run`. Metin ~2 saniyelik parçalara (shot) bölünür → `storyboard.yaml`.
3. **Görselleri planla:** `python -m studio plan 002-born-to-run`
   - *manual (ücretsiz):* `build/planner_prompt.md` dosyası oluşur. İçeriğini Claude'a yapıştır, gelen YAML cevabı
     `plan.yaml` olarak kaydet: `python -m studio apply-plan 002-born-to-run plan.yaml`
   - Daha kolayı: repoyu Claude'a bağla ve "002'yi planla" de. Talimatlar `CLAUDE.md` içinde.
4. **Üret:** `python -m studio all 002-born-to-run` (ses → zamanlama → görseller → video)
5. **Kontrol:** `python -m studio sheet 002-born-to-run` bütün sahneleri tek resimde gösterir.
   Beğenmediğin shot'un `visual` kısmını `storyboard.yaml`'da düzelt ve `all`'u tekrar çalıştır.
   Sadece değişen shot'lar yeniden üretilir, değişmeyen ses ve görseller önbellekten gelir.

Diğer komutlar: `voice`, `align`, `images [--only s001,s002] [--force]`, `render`, `status`, `catalog`, `refs`.

## Görsel sistemi

Bir sahne birkaç satırlık bir tariftir. Tam biçim: [docs/STORYBOARD.md](docs/STORYBOARD.md)

```yaml
visual:
  bg: savanna                      # 11 arka plan
  bg_opts: {sun: low, hut: true}
  figures:                         # 20 poz, yüz ifadeleri, aksesuarlar, ellerde nesneler
    - {pose: kneel_grind, x: 780, wear: [hair_bun, hide], face: focused, sweat: true}
  props:                           # 40 nesne
    - {type: quern, x: 1115}
```

Neler çizilebildiğini görmek için: `docs/catalog/poses.png`, `props.png`, `backgrounds.png`.

**Karma kullanım:** Kodla çizilemeyecek bir sahne (kalabalık, detaylı manzara) için sadece o shot'a
`engine: gemini` ve `visual: {prompt: "..."}` yaz. Videonun geri kalanı ücretsiz kalır.
Maskot koçun AI görsellerinde de aynı görünmesi için bir kez `python -m studio refs` çalıştır ve
`visual.characters: [coach]` ekle.

## Ücretli servise geçiş

1. `.env` dosyasına ilgili anahtarı yaz (`GEMINI_API_KEY`, `ELEVENLABS_API_KEY`, `ANTHROPIC_API_KEY`).
   `.env` GitHub'a gönderilmez.
2. `config.yaml`'da ilgili satırı değiştir. Örneğin `tts.provider: elevenlabs` ve `tts.elevenlabs.voice_id`.
3. Aynı komutları çalıştır.

Yaklaşık maliyet, 12 dakikalık ve ~300 görselli bir video için: kodla çizim 0 $; tamamen Gemini ile
fiyatlar modele göre değişir, güncel fiyatlar Google AI Studio'da. ElevenLabs'te ~12.000 karakter.

## Klasörler

```
config.yaml            tüm ayarlar
studio/                kod (tts/, align/, images/, svgkit/, planner/)
docs/STORYBOARD.md     sahne tarifi biçimi (planlayıcının talimatı)
docs/catalog/          çizilebilen her şeyin görsel kataloğu
projects/<video>/      script.md, storyboard.yaml, sources.md; build/ = üretilen dosyalar (Git'e girmez)
assets/music/          fon müzikleri (Git'e girmez; config: audio.music)
```

Testler: `python -m pytest -q`
