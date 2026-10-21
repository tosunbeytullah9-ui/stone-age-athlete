# Ordinary Genius: kanal araştırması ve kararların dayanağı (21 Ekim 2026)

Bu belge kanalın kimliğinin, kapak dilinin ve konu sırasının neye dayandığını gösterir. YouTube'un kendisi bu
oturumdan taranamadı (youtube.com bağlantısı ağ politikasıyla kapalıydı); o kısım panelde Kanal → **YouTube taraması** (ya da `python -m studio scan`) ile sahibin
bilgisayarında yapılacak ve sonuçlar `research/` klasörüne yazılacak.

## 1. Pazar: "nasıl çalışır" nişi
| Kanal | Biçim | Ne gösteriyor |
| --- | --- | --- |
| Branch Education | Yüzsüz, yüksek kaliteli 3D mühendislik | Abonenin üstünde ortalama izlenme (2,6 milyon abone, 3,7 milyon ortalama izlenme) [Autonolab, Şub 2026](https://blog.autonolab.com/niches/2026-02-10-faceless-youtube-engineering/) |
| Animagraffs | Yüzsüz 3D kesit | 1,8 milyon abone, 2,7 milyon ortalama izlenme; aynı kaynak gündelik eşyaların "nasıl çalışır"ını boşluk olarak gösteriyor |
| Jared Owen | Blender 3D, "How does X work?" | 4,3 milyon abone; aynı kaynak fermuar, otomat gibi gündelik eşyaları az işlenmiş buluyor |
| Mustard | Yüzsüz, prodüksiyon ağırlıklı | 1,7 milyon abone, 7,3 milyon ortalama izlenme: kaliteli yüzsüz anlatımın tavanı |

Sonuç: Talep kanıtlı; en iyi büyüyen yüzsüz kanallar mekanizmayı **görsel olarak** kusursuz gösteriyor. Bizim
karşılığımız 3D değil, kodla çizilen ve kelimeye göre hareket eden 2D mekanizma (comp `mech`).

Gelir: Eğitim ve Bilim, 300 kanallık Studio verisinde medyan RPM 10,22 $ ile en yüksek niş; Gadget ve Teknoloji
2,33 $ ([AIR Media-Tech, Tem 2026](https://air.io/en/air-data-findings/which-youtube-niche-makes-the-most-money-in-2026-ranked-by-real-rpm-and-cpm)).
Kanal "Education" kategorisinde, ders tonunda ve 8 dakika üstünde tutulur.

**Yeni açılıp hızla büyüyen kanallar:** Web kaynaklarında kanal açılış tarihi ve büyüme hızı güvenilir biçimde yok.
Bunun için "Yeni kanalları bul" taraması yazıldı: kanalın arama ifadelerinin en yeni videolarından, ilk videosu son 24 ay içinde olup
10 bin aboneye ya da 100 bin izlenmeli bir videoya ulaşmış kanalları listeler.

## 2. Kapak araştırması
- vidIQ, Haziran 2026'da patlayan 500 uzun videonun kapağı: %69'unda insan yüzü, %56'sında yüksek kontrast,
  %89'unda ikisinden biri; yazılı kapaklarda medyan 5 kelime; abartılı ifade sadece %5
  ([vidIQ Research, Tem 2026](https://vidiq.com/research/youtube-thumbnail-study/)).
- vidIQ önerisi: YouTube'un kırmızı-beyaz-siyahından kaçın, turuncu, turkuaz, sarı, mor kullan; 3–5 kelime; sağ alt
  köşe boş; tek odak ([vidIQ blog](https://vidiq.com/blog/post/youtube-thumbnail-design-tips/)).
- TubeAnalytics 2025–2026: parlak, doygun arka plan +%8–14 CTR; 3–5 kelimelik yüksek kontrastlı yazı aramada +%11–22
  ([TubeAnalytics](https://www.tubeanalytics.net/resources/research/thumbnail-ctr-patterns-study-2026)).

**Karar:** Yüz yok (kanal yüzsüz), yerine kodla çizilmiş dev, kusursuz bir nesne; gizli parça sarı parlar;
koyu çivit sahne üstünde doygun renkler; beyaz Anton yazı, kalın lacivert kontur, 2–4 kelime. Üç tür (Sahne,
Düzeltme, Damga "SOLVED") Test & Compare'de yarışır. Yüzsüzlük bir dezavantaj: 10 videodan sonra veriye göre bir
"el" ya da basit bir karakter yüzü denenebilir. "Rakip kapaklarını topla" taraması rakiplerin kapaklarını tek sayfada toplar.

## 3. Amerikan evinde ne var (konu seçimi)
| Eşya | ABD'de yaygınlık | Kaynak |
| --- | --- | --- |
| Ocak-fırın (range) | evlerin %87'si | [EIA RECS 2024](https://www.eia.gov/consumption/residential/data/2024/pdf/RECS%20HC%20Flipbook%202026.pdf) |
| Çamaşır makinesi + kurutucu | yaklaşık %83 | EIA RECS 2024 |
| Bulaşık makinesi | %74 | EIA RECS 2024 |
| Hava fritözü | %71 | [NFRA, Eyl 2026](https://perishablenews.com/?p=435411) |
| Konserve açacağı, ölçü kabı-kaşığı, spatula | yetişkinlerin en az %90'ı | [YouGov, Kas 2023](https://yougov.com/en-us/articles/47875-how-common-are-your-kitchen-utensils) |
| Biftek bıçağı, kesme tahtası, çırpıcı, soyacak, maşa | %80'in üstü | YouGov, Kas 2023 |

Fikir havuzu (`ideas.yaml`, 37 fikir) bu listeyle ve Amerikan evine özgü eşyalarla (çöp öğütücü, garaj kapısı,
duman dedektörü) kuruldu. Rekabet: "Konuları tara" her fikir için ilk 20 videoyu, güçlü videoları ve
"son iki yılda güçlü, uzun video yok" boşluğunu yazar. Talep bantları için ayrıca `python -m studio signals`.

## 4. Üretim modeli
- Resimlerin %85–90'ı kodla: Remotion `mech` (kelime kelime zamanlama, `@kelime` işaretleri). Gemini sadece insan,
  mekân ve tarih sahnelerinde, kanalın düz vektör üslubuyla (pilotta 52 sahneden 6'sı, ~0,30 $).
- Ses: Gemini TTS (Zephyr; pilotta Leda ile karşılaştırılacak). Müzik: YouTube Audio Library, enstrümantal.
- Senaryo: çarpıcı gerçek → nesne → eskiden → fizik (orta bölümün %55–65'i, her fikre bir metafor) → bugün →
  yeni kelimelerle kısa özet ve sonraki nesneye köprü. Tekrar yok (fabrikanın 6 kelimelik örtüşme denetimi).

## 5. İlk YouTube taraması (21 Ekim, sahibin bilgisayarında)
- **g001 konserve açacağı: BOŞLUK.** `how does a can opener work` aramasının ilk 20 videosu: medyan 148 bin izlenme,
  11 güçlü video (≥100 bin), ama son iki yılda 8 dakikadan uzun güçlü video yok (`rakip-2026-10-21.md`).
- **Talep "nasıl kullanılır" tarafında:** en büyük video 2 dakikalık bir kullanım dersi (4,3 milyon, 2016). İnsanlar
  aleti yüzeyde biliyor, içini bilmiyor: kanalın vaadiyle örtüşüyor.
- **Tek uzun rakip:** Technology Connections, "Lessons from a Can Opener" (2022, 21 dk, 3 milyon). İzleyici yorumlarına
  göre ağırlığı yandan kesen güvenli açacak, kullanım ve konserve kültürü. Bizim açımız farklı: üç basit makine,
  basınç ve gerilme, kenarın içindeki çift dikiş (beş kat metal) ve krank turu geometrisi (π sadeleşir).
- **Kapaklar** (`research/kapaklar/kontak.jpg`, 16 konunun en çok izlenen 3'er videosu; sadece inceleme, repoya
  girmez): konserve açacağında üç kapağın üçü de elle tutulan aletin gerçek fotoğrafı, kodla çizilmiş tek nesne bu
  aramada ayrışıyor. Temiz çizilmiş kesit + büyük kısa yazı başka konularda milyonlar alıyor (Jared Owen: kilit
  5,1 milyon, tükenmez kalem 0,9 milyon). Rakip olarak en sık çıkan kanal Technology Connections: duman dedektörü,
  kahve makinesi, perkolatör, hava fritözü ve konserve açacağında ilk üçte. Bu konularda açımızı onun videosundan
  ayırmak şart; fermuarda Veritasium (9,8 milyon) var.
- **Yeni kanallar:** ilk tarama boş döndü. Sebep taramanın kendisiydi: sadece en yeni yüklemelere bakıyordu ve yeni
  yüklemelerin neredeyse hepsi 20 bin izlenmenin altında. Düzeltildi (en alakalı videolar da taranıyor, rapor kaç
  kanalın neden elendiğini yazıyor); tarama tekrar çalıştırılmalı.
