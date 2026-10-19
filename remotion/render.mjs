// Batch renderer called by the Python pipeline (studio/remotion.py):  node render.mjs <jobs.json>
//
// jobs.json: {"jobs": [{"id", "comp", "kind": "video"|"still", "props", "frames", "fps", "width", "height",
//                        "out", "frame"?, "crf"?}], "concurrency"?: n, "browser"?: path}
// One bundle and one browser for all jobs. Prints "OK <id>" / "FAIL <id> <message>" per job; exit 1 if any failed.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {bundle} from '@remotion/bundler';
import {ensureBrowser, openBrowser, renderMedia, renderStill, selectComposition} from '@remotion/renderer';

const here = path.dirname(fileURLToPath(import.meta.url));
const spec = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const jobs = spec.jobs ?? [];
const browserExecutable = spec.browser || process.env.REMOTION_BROWSER || null;
const concurrency = spec.concurrency || null;

if (!jobs.length) process.exit(0);
console.log(`remotion: ${jobs.length} iş, paketleniyor...`);
const serveUrl = await bundle({
  entryPoint: path.join(here, 'src', 'index.ts'),
  publicDir: path.join(here, 'public'),
  onProgress: () => undefined,
});
if (!browserExecutable) await ensureBrowser(); // first run downloads Chrome Headless Shell once
const browser = await openBrowser('chrome', {browserExecutable});

let failed = 0;
for (const job of jobs) {
  const inputProps = {...(job.props ?? {}), frames: job.frames, fps: job.fps, width: job.width, height: job.height};
  try {
    const composition = await selectComposition({serveUrl, id: job.comp, inputProps, puppeteerInstance: browser, browserExecutable});
    fs.mkdirSync(path.dirname(job.out), {recursive: true});
    if (job.kind === 'still') {
      const tmp = job.out.replace(/\.png$/i, '') + '.part.png';
      await renderStill({
        composition,
        serveUrl,
        output: tmp,
        inputProps,
        frame: Math.min(composition.durationInFrames - 1, Math.max(0, job.frame ?? composition.durationInFrames - 1)),
        puppeteerInstance: browser,
        browserExecutable,
        imageFormat: 'png',
        overwrite: true,
      });
      fs.renameSync(tmp, job.out);
    } else {
      const tmp = job.out.replace(/\.mp4$/i, '') + '.part.mp4';
      await renderMedia({
        composition,
        serveUrl,
        codec: 'h264',
        outputLocation: tmp,
        inputProps,
        crf: job.crf ?? 18,
        pixelFormat: 'yuv420p',
        muted: true,
        concurrency,
        puppeteerInstance: browser,
        browserExecutable,
        overwrite: true,
      });
      fs.renameSync(tmp, job.out);
    }
    console.log(`OK ${job.id}`);
  } catch (err) {
    failed += 1;
    console.log(`FAIL ${job.id} ${String(err?.message ?? err).split('\n')[0]}`);
  }
}
await browser.close({silent: true});
process.exit(failed ? 1 : 0);
