import {spawnSync} from 'node:child_process';

const [sourcePath, outputPath] = process.argv.slice(2);
if (!sourcePath || !outputPath) {
  console.error('Usage: node verify-video.mjs <source-video> <rendered-video>');
  process.exit(2);
}

const probe = (path) => {
  const result = spawnSync('ffprobe', ['-v', 'error', '-show_entries', 'stream=codec_type,r_frame_rate,duration,width,height', '-of', 'json', path], {encoding: 'utf8'});
  if (result.status !== 0) throw new Error(result.stderr || `ffprobe failed: ${path}`);
  return JSON.parse(result.stdout).streams;
};
const rate = (value) => {
  const [numerator, denominator] = value.split('/').map(Number);
  return denominator === 0 ? 0 : numerator / denominator;
};

const sourceStreams = probe(sourcePath);
const outputStreams = probe(outputPath);
const sourceVideo = sourceStreams.find((stream) => stream.codec_type === 'video');
const outputVideo = outputStreams.find((stream) => stream.codec_type === 'video');
const outputAudio = outputStreams.find((stream) => stream.codec_type === 'audio');
if (!sourceVideo || !outputVideo || !outputAudio) throw new Error('Missing source video or output audio/video stream');

const sourceFps = rate(sourceVideo.r_frame_rate);
const outputFps = rate(outputVideo.r_frame_rate);
const drift = Math.abs(Number(outputVideo.duration) - Number(outputAudio.duration));
if (outputFps + 0.01 < sourceFps) throw new Error(`Output FPS ${outputFps} is lower than source FPS ${sourceFps}`);
if (outputVideo.width < sourceVideo.width || outputVideo.height < sourceVideo.height) {
  throw new Error(`Output ${outputVideo.width}x${outputVideo.height} is smaller than source ${sourceVideo.width}x${sourceVideo.height}`);
}
if (!Number.isFinite(drift) || drift > 0.1) throw new Error(`A/V duration drift ${drift.toFixed(3)}s exceeds 0.1s`);

console.log(JSON.stringify({
  source: {fps: sourceFps, width: sourceVideo.width, height: sourceVideo.height},
  output: {fps: outputFps, width: outputVideo.width, height: outputVideo.height},
  avDriftSeconds: drift,
}, null, 2));
