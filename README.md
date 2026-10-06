# Video Fabrikası

Birden çok YouTube kanalını tek bir üretim hattından çalıştıran, **senin bilgisayarında** çalışan bir video fabrikası.
Web panelinden yönetilir. Başlangıçta her şey **ücretsiz** çalışır; iş büyüdüğünde her aşama tek ayarla ücretli
servise geçer, kodda değişiklik gerekmez.

Akış: fikir havuzu (talep/rekabet sinyalleriyle) → senaryo → iddialar ve kaynaklar → storyboard → seslendirme →
görseller → video, Shorts, altyazı, ek dil ses izi → kapak ve başlık → yayın takvimi → performans ve izlenme eğrisi.

İlk kanal: **Homo Athleticus**, bir kuvvet ve kondisyon koçunun anlatımıyla insan bedeninin hikâyesi
([marka mimarisi](docs/BRAND.md)).

![Üretim ekranı](docs/img/production.png)

## Başlatma

1. Bir kez kur: **Python 3.12** (3.10–3.13 arası; 3.14 henüz desteklenmiyor), **FFmpeg** ve **Git**
   - Windows: `winget install Python.Python.3.12 Gyan.FFmpeg Git.Git`
   - Mac: `brew install python ffmpeg git`
2. Repoyu indir: `git clone https://github.com/tosunbeytullah9-ui/video-fabrikasi.git`
3. **Windows:** `start.bat` dosyasına çift tıkla. **Mac:** `./start.sh`
   - İlk açılışta kurulum birkaç dakika sürer.
   - Sonra panel tarayıcıda kendiliğinden açılır: http://127.0.0.1:8765

Panel sadece senin bilgisayarında çalışır, internete açılmaz.

## Güncelleme

**Windows:** `guncelle.bat` dosyasına çift tıkla. **Mac:** `./guncelle.sh`.

Yeni sürüm indirilir, senin yerel değişikliklerin (fikir durumları, projeler, senaryolar, ayarlar) korunur ve
değer değer birleştirilir. Her şeyin bir kopyası `backups/` klasörüne alınır. Aynı dosya iki tarafta da değiştiyse
senin sürümün `<dosya>.senin-surumun` adıyla yanına bırakılır. `git pull`'u elle çalıştırmana gerek yok.

## Bir video nasıl üretilir (panelden)

| Adım | Nerede | Ne olur |
| --- | --- | --- |
| 1. Fikri seç | Kanal → **Fikir havuzu** | 152 fikir. "Sinyalleri güncelle" YouTube'daki talep, rekabet ve boşluğu ölçer. Sezgi puanını ver, "Projeye dönüştür" |
| 2. Senaryo | Proje → **1 · Senaryo & kaynaklar** | Şablon yapıyı gösterir: kanca, kanıt, dönüş, coach's lesson |
| 3. İddialar | Aynı sekme → **İddialar** | İstemi Claude'a ver. Her iddia bir kaynağa ve cümleye bağlanır; kaynaklar ortak kütüphaneye girer. Doğrulayınca işaretle |
| 4. Planla | **2 · Storyboard** | Plan istemi → Claude → "Planı uygula". Yakın çekim için `frame` |
| 5. Üret | **3 · Üretim** | Ses, zamanlama, görseller, video, altyazı (.srt). Videoda: aynı sahnede yumuşak geçiş, büyüyen grafikler, ekran yazıları (dile göre), ses efektleri, konuşurken kısılan müzik, 18 sn kapanış sahnesi. Shorts dikey çizilir, altyazılıdır. Türkçe için "Ek ses izi" |
| 6. Paketle | **4 · Kapak & başlık** | Paket istemi: 10 başlık, 3 kapak konsepti, açılış ve Shorts önerileri. Kapakları üret, telefon boyutunda karşılaştır |
| 7. Çıktılar | **5 · Çıktılar** | Video, Shorts, altyazı, ek ses izi ve kaynaklı YouTube açıklaması |
| 8. Yayınla | **6 · Yayın & performans** | Seri, açılış tipi, tahmin, YouTube id. 2., 7. ve 28. günde ölçümler. İzlenme eğrisini yapıştır: izleyicinin hangi cümlede ve hangi çizimde gittiği görünür |
| Marka | Kanal → **Kanal ayarları** | "Marka görsellerini üret": profil resmi, banner (güvenli alan kılavuzlu), filigran. "Bilgi paketini üret": kanalın tamamını tek dosyada toplayan `knowledge.md`; Claude Project / ChatGPT / DeepSeek'e bilgi olarak yüklenir |
| Takvim | Kanal → **Takvim** | Haftalık yayın günleri (varsayılan Pzt/Çar/Cum), boş slotlara proje yerleştirme, geciken projeler kırmızı |

Kaynak kütüphanesi (sol menü) tüm kanalların ortak kaynaklarını gösterir ve bağlantıları kontrol eder.

![Sahne düzenleyici](docs/img/shot-editor.png)

## Ücretsizden ücretliye

Panel → **Ayarlar**: anahtarı yapıştır, ilgili satırı değiştir. Anahtarlar sadece bilgisayarındaki `.env` dosyasında durur.

| Aşama | Ücretsiz (varsayılan) | Ücretli |
| --- | --- | --- |
| Görsel planı, çeviri, iddialar, paket | `planner.provider: manual` (Claude sohbeti) | `anthropic` (otomatik plan ve çeviri) |
| Ses (İngilizce) | `kokoro` (yerel) | `elevenlabs` |
| Ses (Türkçe) | `edge` (çevrimiçi) | `elevenlabs` |
| Sesli duygu (etiket) | – | `elevenlabs` + `model: eleven_v3`: script.md'de `[curious]`, `[excited]`, `[whispers]`, `[pause]` |
| Görseller | `svg` (kodla çizim) | `gemini` (Nano Banana). Tek shot için de seçilebilir |
| Fikir sinyalleri | YouTube Data API anahtarı (ücretsiz, günde ~95 fikir) | – |

Her kanal bu ayarları kendi `channel.yaml → overrides` bölümünde ezebilir.

## YouTube politikasına karşı koruma

YouTube şablonla seri üretilen içeriği para kazanmadan çıkarıyor. **Kalite kapısı** bir projeyi şu durumlarda
"hazır" saymaz:

- senaryo 150 kelimenin altındaysa,
- iddiaların kaynağı kütüphanede yoksa,
- 3'ten az farklı kaynak varsa,
- planlanmamış shot varsa.

Şu durumlarda da uyarır:

- doğrulanmamış iddia,
- iddiaya bağlanmamış sayı,
- kaynağın söylediğinden fazlasını söyleyen cümle,
- tek arka plana aşırı yaslanma,
- art arda tekrar eden sahne.

## Klasörler

```
config.yaml                          genel ayarlar (panel → Ayarlar)
library/sources.yaml                 ortak kaynak kütüphanesi (tüm kanallar)
channels/<kanal>/channel.yaml        kimlik, seriler, yayın takvimi, kanala özel ayarlar
channels/<kanal>/ideas.yaml          fikir havuzu (+ sinyaller, sezgi puanı)
channels/<kanal>/projects/<video>/   script.md, sources.md, claims.yaml, storyboard.yaml, project.yaml (kapaklar,
                                     yayın kaydı), analytics/ (izlenme eğrisi), build/ (üretilenler, Git dışı)
studio/                              üretim hattı (tts, align, images, svgkit, planner, render, claims, thumbnails,
                                     dub, publish, schedule, retention, signals, updater, web)
docs/BRAND.md · docs/STORYBOARD.md · docs/FACTORY.md · docs/catalog/
```

Komut satırı da var (panel aynı komutları kullanıyor): `python -m studio --help`. Testler: `python -m pytest -q`
