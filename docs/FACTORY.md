# Fabrika mimarisi ve büyüme planı

## Hedef

Bugün sıfır sabit maliyetle çalışan, yarın yatırımla ölçeklenen bir içerik üretim altyapısı.
Kanal eklemek veri eklemektir, kod yazmak değil. Ücretli servise geçmek bir ayardır, yeniden yazım değil.

## Katmanlar

```
Panel (studio/web)           kanallar · fikir havuzu + sinyaller · takvim · senaryo + iddialar · storyboard · üretim ·
                             kapak & başlık · çıktılar · yayın & performans · kaynak kütüphanesi · işler · ayarlar
   │  HTTP (127.0.0.1)
İş kuyruğu (web/jobs.py)     her adım ayrı süreç: çökme paneli etkilemez, günlük canlı akar
   │  python -m studio <adım>
Üretim hattı (studio/)
   split → storyboard → planner → [translate] → tts → align → images → render → describe(+srt) / shorts / dub
   claims (iddia ↔ kaynak ↔ shot) · thumbnails (paket) · publish (yayın kaydı) · schedule (takvim)
   retention (izlenme eğrisi → shot) · signals (YouTube Data API) · updater (güvenli güncelleme) · migrate
   │               sağlayıcı arayüzleri (config ile seçilir)
Sağlayıcılar
   planner:  manual (Claude sohbeti)          | anthropic (API)
   tts:      kokoro (yerel) · edge (çevrimiçi) | elevenlabs
   align:    proportional · whisper            | sağlayıcıdan kesin zaman (ElevenLabs, Edge)
   images:   svg (kodla çizim)                 | gemini (Nano Banana)
Veri (Git'te, güncellemede değer değer birleştirilir)
   library/sources.yaml   channels/<kanal>/{channel.yaml, ideas.yaml, projects/<video>/{script.md, claims.yaml,
   storyboard.yaml, project.yaml, analytics/}}   ·   build/ (üretilenler, Git dışı, içerik hash'iyle önbellekli)
```

## Önemli tasarım kararları

- **Görsellerde yazı yok.** Bir sahne her dilde aynen kullanılır. Türkçe/İspanyolca sürüm sadece çeviri + ses maliyeti.
- **Shot düzeyinde çeviri.** Her görsel kendi cümlesinin çevirisiyle eşleşir, zamanlama bozulmaz.
- **İçerik hash'iyle önbellek.** Değişmeyen shot'un görseli ve cümlenin sesi yeniden üretilmez, yeniden ücret ödenmez.
- **Kalite kapısı.** Kaynaksız, kısa ya da tekrarlı proje "hazır" sayılmaz (YouTube Temmuz 2026 politikası).
- **Her adım ayrı süreç.** Panel hafif kalır, adımlar tek tek ya da toplu çalıştırılabilir.

## Maliyet modeli (12 dk, ~300 shot'luk bir video)

| Kurulum | Planlama | Ses | Görsel | Toplam |
| --- | --- | --- | --- | --- |
| Tamamen ücretsiz (bugün) | Claude sohbeti | Kokoro / Edge | svg | 0 $ (+ zaman) |
| Karma | Claude sohbeti | Kokoro | svg + ~20 Gemini shot | ~1–2 $ |
| Otomatik | Anthropic API | ElevenLabs | svg + Gemini | API fiyatlarına göre (Google AI Studio / ElevenLabs / Anthropic fiyat sayfaları) |

## Yol haritası

| Aşama | Ne | Neden |
| --- | --- | --- |
| 1 (şimdi) | Homo Athleticus, 10–20 video, ücretsiz akış + ElevenLabs Creator | Hangi serinin tuttuğunu ölçmek |
| 2 | Türkçe ek ses izi, amaca yazılmış Shorts, uyku derlemeleri | Aynı araştırmadan 4–5 çıktı |
| 3 | Yayın kayıtları + izlenme eğrileri ile ilk karşılaştırmalar (açılış tipi, seri, süre) | 20–30 videoda "neden" sorusu |
| 4 | Ekran üstü katman (sayılar, etiketler, kaynak künyesi, dile göre), basit animasyon ve ses efekti | İzleyiciyi tutma |
| 5 | Otomatik planlama (Anthropic) + YouTube Analytics API ile ölçümlerin otomatik gelmesi | Operasyon süresini düşürmek |
| 6 | 2. kanal (Tıp Tarihi): aynı çekirdek, ortak kaynak kütüphanesi | Görsel ve kaynak kütüphanesini yeniden kullanmak |

## Genişleme nişleri (araştırma, Eylül 2026)

Öncelik sırası: **Tıp tarihi → Paranın/ekonominin tarihi → Günlük yaşam tarihi → Hayvan biyolojisi → Mitoloji**.
Kanıtlar ve rekabet için: Claude Docs'taki "Niş Araştırması: İnsan Bedeni × Tarih" dokümanı.
