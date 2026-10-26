# Thumbnails (three kinds per channel)

Every video gets three thumbnails, one of each of its channel's kinds, and all three go into YouTube Studio's
**Test & Compare**.
It picks the winner by watch-time share, not clicks, so a misleading thumbnail loses. After about ten videos per
channel, the kind that wins most often becomes that channel's default.

| kind | what it shows | words |
|---|---|---|
| `correction` | the belief in big letters, struck through by hand in the accent colour; a handwritten note under it | `myth` ≤ 3 short words or one number, `note` ≤ 3 words |
| `stamp` | one object drawn large, a rubber stamp on its empty side | none (the stamp word: channel default or `stamp`) |
| `scene` | a moment that really happens in the video | `text` ≤ 3 words |
| `loupe` | the object huge; a magnifying lens shows the one small part that does the trick, enlarged | `text` ≤ 3 words |
| `xray` | the object split by a glowing scan line: the outside on one side, its mechanism on the other | `text` ≤ 3 words |
| `tag` | the object huge; rings around one small part and a thick arrow from a yellow part tag | `text` ≤ 3 words (on the tag) |

## Each channel has its own three kinds
Two channels of the same owner must not share one thumbnail grammar: a viewer (and YouTube's spam review, which looks
at "coordinated networks of channels" and "repetitive AI-generated imagery") should never feel two channels are one
template. `channel.yaml → thumbnails.kinds` picks the set; the packaging and preparation prompts, `prep-check`, the
channel bible, the panel and the preview all follow it.

| channel | kinds | grammar |
|---|---|---|
| You're Wrong! (default set) | `correction`, `stamp`, `scene` | a myth struck through, stamped, handwritten |
| Ordinary Genius | `loupe`, `xray`, `tag` | the object is the hero, the hidden part is the question |

```yaml
# object kinds (coordinates on the 1920×1080 design canvas, after `frame`)
- kind: loupe
  visual: {comp: mech, items: [...]}
  focus: {x: 1013, y: 573, r: 130}     # the small part
  lens: {x: 480, y: 395, r: 235}       # where the enlarged lens goes (empty side)
  handle: 225                          # lens handle angle in degrees (false = no handle)
  text: {en: TWO TINY WHEELS}
  pos: top-right
- kind: xray
  visual: {comp: mech, items: [...]}   # the outside
  inside: {comp: mech, items: [...], bg: {color: "#0d1b45"}}   # the same drawing cut open, same place and size
  split: {x: 790, angle: 7}            # the scan line; `side: left` shows the inside on the left; `tint: true`
  text: {en: WHAT'S INSIDE?}           #   turns an AI-painted inside into a blueprint
  pos: top-left
- kind: tag
  visual: {comp: mech, items: [...]}
  point: {x: 1069, y: 757, r: 110}     # the part the arrow points at
  text: {en: WHY TEETH?}               # a question, or a number with its claim
  pos: top-left
```
An `xray` thumbnail costs two pictures when painted by Gemini (both are free when drawn by code).

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
- `myth` longer than 3 words
- `note` or `text` longer than 3 words
- a `loupe` without `focus`/`lens`, an `xray` without `inside`, a `tag` without `point`
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
  kinds: [correction, stamp, scene]   # this channel's three kinds (see above)
  outline: null              # vivid look: words in `text_fill` with a thick outline in this colour, no paper slip
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
