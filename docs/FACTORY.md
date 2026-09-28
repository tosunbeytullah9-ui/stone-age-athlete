# Fabrika mimarisi ve büyüme planı

## Hedef

Bugün sıfır sabit maliyetle çalışan, yarın yatırımla ölçeklenen bir içerik üretim altyapısı.
Kanal eklemek veri eklemektir, kod yazmak değil. Ücretli servise geçmek bir ayardır, yeniden yazım değil.

## Katmanlar

```
Panel (studio/web)           kanallar · fikir havuzu · senaryo · storyboard · üretim · çıktılar · işler · ayarlar
   │  HTTP (127.0.0.1)
İş kuyruğu (web/jobs.py)     her adım ayrı süreç: çökme paneli etkilemez, günlük canlı akar
   │  python -m studio <adım>
Üretim hattı (studio/)
   splitter → storyboard → planner → [translate] → tts → align → images → render → describe / shorts / compile
   │               sağlayıcı arayüzleri (config ile seçilir)
Sağlayıcılar
   planner:  manual (Claude sohbeti)          | anthropic (API)
   tts:      kokoro (yerel) · edge (çevrimiçi) | elevenlabs
   align:    proportional · whisper            | sağlayıcıdan kesin zaman (ElevenLabs, Edge)
   images:   svg (kodla çizim)                 | gemini (Nano Banana)
Veri
   channels/<kanal>/ (yaml + md dosyaları, Git'te)   build/ (üretilenler, Git dışı, içerik hash'iyle önbellekli)
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
| 1 (şimdi) | Tek kanal, ücretsiz akış, 10 video | Hangi sütunun tuttuğunu ölçmek |
| 2 | Türkçe ayna yayın, Shorts ve uyku derlemeleri | Aynı işten 4–5 çıktı |
| 3 | 2. kanal: Tıp Tarihi. Yeni nesneler: cerrahi aletler, anatomi | Görsel kütüphaneyi en çok yeniden kullanan niş |
| 4 | Otomatik planlama (Anthropic) + ElevenLabs | Senaryo sonrası tamamen tek tuş |
| 5 | Yayın otomasyonu: YouTube Data API ile yükleme, planlama, kapak testleri | Operasyon süresini düşürmek |
| 6 | Analitik geri besleme: izlenme verisini fikir havuzuna bağlamak | Hangi fikirlerin önce üretileceğini veri seçer |

## Genişleme nişleri (araştırma, Eylül 2026)

Öncelik sırası: **Tıp tarihi → Paranın/ekonominin tarihi → Günlük yaşam tarihi → Hayvan biyolojisi → Mitoloji**.
Kanıtlar ve rekabet için: Claude Docs'taki "Niş Araştırması: İnsan Bedeni × Tarih" dokümanı.
