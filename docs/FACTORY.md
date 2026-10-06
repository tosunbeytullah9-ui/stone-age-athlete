# Fabrika mimarisi ve büyüme planı

## Hedef

Bugün sıfır sabit maliyetle çalışan, yarın yatırımla ölçeklenen bir içerik üretim altyapısı.
Kanal eklemek veri eklemektir, kod yazmak değil. Ücretli servise geçmek bir ayardır, yeniden yazım değil.

## Katmanlar

```
Panel (studio/web)           kanallar · fikir havuzu + sinyaller · takvim · proje: 1 senaryo + iddialar → 2 sahneler →
                             3 video → 4 kapak & başlık → 5 yayın · kaynak kütüphanesi · işler · ayarlar
   │  HTTP (127.0.0.1)
İş kuyruğu (web/jobs.py)     her adım ayrı süreç: çökme paneli etkilemez, günlük canlı akar
   │  python -m studio <adım>
Üretim hattı (studio/)
   split (shot = altyazı/çeviri birimi) → planner (sahne = 2–4 shot, bir resim) → [translate] → tts → align →
   images (sahne başına bir resim) → render (sahne boyunca tek kamera hareketi) → describe(+srt) / shorts / dub
   claims (iddia ↔ kaynak ↔ shot) · thumbnails (paket) · publish (yayın kaydı) · schedule (takvim)
   retention (izlenme eğrisi → shot) · signals (YouTube Data API) · updater (güvenli güncelleme) · migrate
   │               sağlayıcı arayüzleri (config ile seçilir)
Sağlayıcılar
   planner:  gemini (tek tık) · anthropic (API) · manual (Claude sohbeti)
   tts:      kokoro (yerel) · edge (çevrimiçi) | gemini · elevenlabs
   align:    proportional · whisper            | sağlayıcıdan kesin zaman (ElevenLabs, Edge)
   images:   gemini (Nano Banana, kanal stili + karakter referansı) · grafikler: svg (kodla, kanalın kâğıdına basılı)
Veri (Git'te, güncellemede değer değer birleştirilir)
   library/sources.yaml   channels/<kanal>/{channel.yaml, ideas.yaml, projects/<video>/{script.md, claims.yaml,
   storyboard.yaml, project.yaml, analytics/}}   ·   build/ (üretilenler, Git dışı, içerik hash'iyle önbellekli)
```

## Önemli tasarım kararları

- **Görsellerde yazı yok.** Bir sahne her dilde aynen kullanılır. Türkçe/İspanyolca sürüm sadece çeviri + ses maliyeti.
- **Shot düzeyinde çeviri, sahne düzeyinde resim.** Altyazı, ekran yazısı ve çeviri kısa cümle parçalarına (shot) bağlı;
  bir resim 2–4 shot boyunca ekranda kalır ve kamera üzerinde kesintisiz hareket eder. Böylece video başına ~180 değil
  ~60–90 resim gerekir.
- **Tek görsel dil.** Stil cümlesi ve karakter referansı her istemle gider; kanal tanınır, koç her videoda aynı kişidir.
- **İçerik hash'iyle önbellek.** Değişmeyen sahnenin resmi ve cümlenin sesi yeniden üretilmez, yeniden ücret ödenmez.
- **Kalite kapısı.** Kaynaksız, kısa ya da tekrarlı proje "hazır" sayılmaz (YouTube Temmuz 2026 politikası).
- **Her adım ayrı süreç.** Panel hafif kalır, adımlar tek tek ya da toplu çalıştırılabilir.

## Maliyet modeli (~9 dk, ~60 sahnelik bir video)

| Kalem | Varsayılan | Yaklaşık |
| --- | --- | --- |
| Sahne planı + çeviri | Gemini (gemini-3.8-flash) | ~0,05 $ |
| Resimler | Gemini 3.1 Flash Image, 1K | ~0,05 $ × 55 ≈ 3 $ |
| Ses | Gemini TTS (kanal ayarı) / Kokoro ücretsiz | ~0,25 $ / 0 $ |
| Grafikler, kurgu, altyazı, Shorts | yerel | 0 $ |

Daha keskin resim: `images.gemini.image_size: "2K"`; daha tutarlı karakter: `gemini-3-pro-image` (yaklaşık 3 kat).
Güncel fiyatlar için Google AI Studio fiyat sayfasına bak.

## Yol haritası

| Aşama | Ne | Neden |
| --- | --- | --- |
| 1 (şimdi) | Homo Athleticus, 10–20 video, ücretsiz akış + ElevenLabs Creator | Hangi serinin tuttuğunu ölçmek |
| 2 | Türkçe ek ses izi, amaca yazılmış Shorts | Aynı araştırmadan 3–4 çıktı |
| 3 | Yayın kayıtları + izlenme eğrileri ile ilk karşılaştırmalar (açılış tipi, seri, süre) | 20–30 videoda "neden" sorusu |
| 4 | Ekran üstü katman (sayılar, etiketler, kaynak künyesi, dile göre), basit animasyon ve ses efekti | İzleyiciyi tutma |
| 5 | YouTube Analytics API ile ölçümlerin otomatik gelmesi | Operasyon süresini düşürmek |
| 6 | 2. kanal (Tıp Tarihi): aynı çekirdek, ortak kaynak kütüphanesi | Görsel ve kaynak kütüphanesini yeniden kullanmak |

## Genişleme nişleri (araştırma, Eylül 2026)

Öncelik sırası: **Tıp tarihi → Paranın/ekonominin tarihi → Günlük yaşam tarihi → Hayvan biyolojisi → Mitoloji**.
Kanıtlar ve rekabet için: Claude Docs'taki "Niş Araştırması: İnsan Bedeni × Tarih" dokümanı.
