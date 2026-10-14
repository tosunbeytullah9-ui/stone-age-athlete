# Thumbnails (three kinds, every channel)

Every video gets three thumbnails, one of each kind, and all three go into YouTube Studio's **Test & Compare**.
It picks the winner by watch-time share, not clicks, so a misleading thumbnail loses. After about ten videos per
channel, the kind that wins most often becomes that channel's default.

| kind | what it shows | words |
|---|---|---|
| `correction` | the belief in big letters, struck through by hand in the accent colour; a handwritten note under it | `myth` ≤ 2 words or one number, `note` ≤ 3 words |
| `stamp` | one object drawn large, a rubber stamp on its empty side | none (the stamp word: channel default or `stamp`) |
| `scene` | a moment that really happens in the video | `text` ≤ 3 words |

The factory prints every word. The AI picture never contains text: its prompt is told to leave the `pos` area
empty.

## project.yaml
```yaml
thumbnails:
  - kind: correction
    visual: {prompt: "Eight drinking glasses standing in a row", characters: []}
    myth: {en: "8 GLASSES"}
    note: {en: "half a sentence?"}
    pos: top-left            # top-left | top | top-right | left | right | bottom-left | bottom (never bottom-right)
    claim: c03               # the claim any number or fact on the thumbnail rests on
  - kind: stamp
    visual: {prompt: "A giant monument of a sports water bottle in a city square"}
    pos: top-left
  - kind: scene
    visual: {prompt: "A plump cheerful grape pointing at a sad shrivelled raisin"}
    text: {en: "NOT A RAISIN"}
    pos: top
    frame: {x: 960, y: 450, zoom: 1.3}   # optional crop (1920×1080 coordinates)
```
Upload the first entry first. If Test & Compare has no clear winner, YouTube shows the first one to everyone.
Older entries without `kind` keep the classic look (big yellow text, `text_pos`, `highlight`).

`python -m studio thumbnails <slug>` paints the pictures (about 0.05 $ each; cached by prompt, so changing words is
free), prints the words and writes `build/thumbnails/<lang>/thumb1..3.png` plus `preview.png`. The preview shows
every variant in the light and the dark feed, at phone home-feed size and at 168 px (sidebar and search). Check it
there: if the words do not read at 168 px, they are too long.

The renderer warns about these rules:
- `myth` longer than 2 words
- `note` or `text` longer than 3 words
- a number with no `claim`
- `pos: bottom-right`

## The channel's look (channel.yaml)
```yaml
thumbnails:
  ink: "#181614"             # letters
  accent: "#b23026"          # strike-through, note, stamp
  stamp: WRONG               # default stamp word
  paper: true                # the pictures are paper pages: warm the page, darken the edges (light-mode feed),
                             # ink multiplied into the paper; false = paintings: words sit on a torn paper slip
  ink_boost: 1               # thicken thin drawn lines (0 for paintings)
  series_tab: true           # coloured index tab on the top edge = the series colour (channel.yaml → series)
  direction: "..."           # optional: how this channel's thumbnail pictures are drawn
  fonts: {title: Anton-Regular.ttf, hand: PermanentMarker-Regular.ttf, stamp: AlfaSlabOne-Regular.ttf}
  size: [1920, 1080]
package:
  positioning: "..."         # what the packaging prompt is told about the channel
  thumbnail_rules: ["..."]   # extra rules for this channel (e.g. a character whose face is never shown)
```
The fonts live in `assets/fonts/` with their licences: Anton and Alfa Slab One under OFL, Permanent Marker under
Apache 2.0. All three may be used commercially. A font added here must have a licence that allows commercial use
and redistribution.

## Rules that do not change
- **One subject.** One subject fills 40–60% of the frame. The rest is plain background.
- **Words.** At most three words, and they add to the title instead of repeating it. Letters are at least a sixth
  of the thumbnail's height.
- **Truth.** Every number and fact on a thumbnail rests on a claim in claims.yaml. The moment shown must be in
  the video.
- **People and brands.** No brand logos and no photos of real people.
- **Repetition.** The same kind is not the default two videos in a row, and the object, composition and words
  always change. Viewers must never feel they have seen this thumbnail before.
- **Bottom-right corner.** Keep it free, because YouTube puts the duration there.
