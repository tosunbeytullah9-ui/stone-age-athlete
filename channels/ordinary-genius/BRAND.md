# Ordinary Genius: brand and writing book

**Promise:** every everyday object is a solved physics problem. Each video opens one object the viewer touches
without thinking — mostly in an American home: kitchen, bathroom, door, desk, garage — and shows the maths, physics,
chemistry or geometry working inside it, and how it was done before.

**Who it is for:** curious adults (US first, any English speaker) who like "how it works" videos but find most of them
either too technical or too shallow. They should leave feeling smarter about something they will use tomorrow.

## The narrator
- A voice only: warm, curious, energetic, American English (Gemini TTS, see `channel.yaml → overrides.tts`). No
  name, no character, no face. It never claims to be an engineer, scientist or expert ("as an engineer…" never).
- Talks to the viewer: "you", "your kitchen drawer". Present tense for how things work.
- Allowed signature: none. No catchphrase intro, no "welcome back" (YouTube's repetitive-content rule). Each video
  writes its own first lines and its own last lines.

## The structure (channel.yaml → package.script_structure)
1. **Striking fact (0–15 s).** The first two or three sentences carry one surprising, sourced fact about the object.
   No greeting, no channel name, no "in this video". Example of the shape, not words to reuse: "The tool in your
   kitchen drawer was invented more than forty years after the thing it opens."
2. **The object.** The moment the viewer uses it, and the one question this video answers.
3. **Then.** How people did the job before — only as much history as makes the mechanism easier to understand.
4. **The physics (55–65 % of the video).** One idea at a time. Each idea:
   - is said in plain words first, then shown on a code-drawn diagram that moves on the exact word;
   - gets exactly one everyday metaphor ("a lever is a see-saw you have bent around a corner");
   - may get one tiny worked example of the maths, said out loud and written on screen as a formula;
   - ends with the question that opens the next idea (a re-hook about every 90 seconds).
5. **Now.** Why today's design looks the way it does and what trade-off it makes.
6. **Close.** A short summary in new words (never a sentence used earlier in the video), then one sentence that
   points at the next object.

Length: 1,200–1,500 words, 8–10 minutes (mid-roll ads start at 8 min).

## Language rules
- **Never repeat.** No sentence, example or metaphor appears twice in a video; the summary restates ideas in new
  words. Across videos, no recycled hooks, closes or metaphors (the factory's 6-word overlap check warns at 12 %).
- Short sentences, mostly under 18 words. One idea per sentence. Plain words: "push" not "apply force", then name
  the term once ("that push is what physicists call force").
- Numbers are written the way they are said ("eighteen fifty-eight", "a quarter of a millimetre"). US units first,
  metric in the same breath when it matters ("about two hundred and fifty degrees Fahrenheit, a hundred and
  twenty-one Celsius").
- Every factual statement is a claim with a source (patent, museum, textbook, standard, manufacturer document,
  government agency). Worked examples that use round illustrative numbers are said as examples ("say you squeeze
  with ten pounds…"), never presented as measurements.
- No brand names in the narration unless history needs them (the 1925 Star Can Opener Company is history; a
  current product brand is not). No product recommendations, no affiliate talk.

## How the pictures are made
- **Code first.** Mechanisms, forces, gears, levers, waves, molecules, formulas and numbers are drawn and animated by
  code (Remotion `comp: mech`, docs/REMOTION.md → mech). They are exact, free, and they move on the exact word
  (`at: "@valve"`). Aim for 75–90 % of the scenes.
- **AI pictures only where code would look poor:** people, historical scenes, places, food. At most 4–8 per video.
  They use `visual_style` (flat vector, thick navy outlines, the same palette, indigo grid stage), so a viewer never
  feels a picture came from somewhere else. Never ask an AI picture to show a mechanism, a number or text.
- Palette (theme `pop`): stage `bg #1b1f4b` with a faint grid; outlines `line #0d1030`; parts `yellow #ffcc33`,
  `coral #ff6b5b`, `teal #2ec4b6`, `violet #9b6bff`, `sky #5ad1ff`, `steel #c9d2e3`; heat `hot`, cold `cold`.
  The part the narration is talking about glows yellow (`glow: yellow`); everything else stays calm.
- One clear subject per scene; the camera moves in when detail matters (`camera` keys), never for decoration.

## Thumbnails
The object is the hero and the hidden part is the question. A viewer sees a thing from their own kitchen drawn
bigger and cleaner than they have ever looked at it, and one small part of it singled out: "wait, what is that?"
Nothing on an Ordinary Genius thumbnail is struck through, stamped or handwritten; that grammar belongs to
You're Wrong!, and two channels of one owner must never look like one template (YouTube spam policy: coordinated
channels, repetitive imagery).

Three kinds per video, one of each, for Test & Compare (`channel.yaml → thumbnails.kinds`; upload `loupe` first):
- **loupe (Büyüteç):** the object huge; a big magnifying lens (yellow rim, coral handle) shows the one small part
  that does the trick, enlarged, joined to it by a light cone. 0–3 words that ask.
- **xray (Röntgen):** the same object twice on one canvas, split by a glowing scan line: the outside everyone knows
  on one side, the mechanism glowing yellow on the other. 0–3 words.
- **tag (Etiket):** the object huge; rings around the small part and one thick yellow arrow from a yellow part tag
  with ≤ 3 navy words: a question ("WHY TEETH?") or a number that is a claim.

Rules:
- Drawn by code (`visual: {comp: mech}`), free and exact; the object fills 45–60 % of the frame and its silhouette
  reads at 168 px. Write the drawings with the project's `scenes.py` helpers so the thumbnail object is the video's
  object.
- Words: white Anton, navy outline and drop shadow; never the title again; a number only with its `claim`.
- No faces, no brands, no logos. Bottom-right corner empty (duration). Never the same object, angle and words twice.

## Accuracy protocol
1. Primary sources first: patents (Google Patents), museum collections, standards and government agencies (EIA,
   EPA, NIST, OSHA), manufacturer technical documents, physics and engineering textbooks.
2. Two independent sources for every historical date or "first".
3. Myths about the object (e.g. "Leonardo invented scissors") are corrected, not repeated as fact.
4. Physics explanations are checked against a textbook or a university page before the script is final.
