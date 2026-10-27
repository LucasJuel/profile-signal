const descriptions = {
  first_photo: ['Your first photo carries the introduction.', 'A clear solo portrait with visible eyes makes it easier to recognize you.'],
  generic_prompts: ['Give a match something specific to ask about.', 'A small story or opinion gives someone a natural opening.'],
  photo_variety: ['Show more than one side of your life.', 'Different distances and settings can make a photo set more informative.'],
  intention: ['Say what kind of connection you want.', 'A warm, direct intention can help people understand whether you are a fit.'],
  negative_framing: ['Frame preferences positively.', 'Describe the kind of behavior you value instead of addressing past matches.'],
  reply_hook: ['Make it easy to start a conversation.', 'A specific question or friendly debate can invite a reply.'],
  story_mismatch: ['Let your photos and words support each other.', 'A coherent profile helps someone picture what spending time with you might be like.']
};
const bars = document.querySelector('#bars');
const spot = document.querySelector('#spotlight');
const status = document.querySelector('#evidenceStatus');
let evidence = null;
let filter = 'all';

function render() {
  if (!evidence) return;
  const themes = evidence.themes.map(theme => ({
    ...theme,
    count: filter === 'all' ? Object.values(theme.counts).reduce((a, b) => a + b, 0) : theme.counts[filter]
  })).sort((a, b) => b.count - a.count);
  const max = Math.max(1, ...themes.map(theme => theme.count));
  bars.replaceChildren();
  themes.forEach(theme => {
    const row = document.createElement('button');
    row.type = 'button';
    row.className = 'bar-row';
    const label = document.createElement('span');
    label.className = 'bar-label';
    label.textContent = theme.name;
    const track = document.createElement('span');
    track.className = 'bar-track';
    const fill = document.createElement('i');
    fill.className = 'bar-fill';
    fill.style.width = (theme.count / max * 100) + '%';
    track.append(fill);
    const count = document.createElement('span');
    count.className = 'bar-score';
    count.textContent = String(theme.count);
    row.append(label, track, count);
    row.addEventListener('click', () => show(theme));
    bars.append(row);
  });
  show(themes[0]);
}

function show(theme) {
  const [titleText, bodyText] = descriptions[theme.id];
  spot.replaceChildren();
  const kicker = document.createElement('span');
  kicker.className = 'kicker';
  kicker.textContent = theme.count + ' CODED THREAD' + (theme.count === 1 ? '' : 'S');
  const title = document.createElement('h3');
  title.textContent = titleText;
  const body = document.createElement('p');
  body.textContent = bodyText;
  const sources = document.createElement('div');
  sources.className = 'source-links';
  const heading = document.createElement('strong');
  heading.textContent = 'Supporting comments';
  sources.append(heading);
  const entries = filter === 'all'
    ? Object.entries(theme.sources).flatMap(([community, urls]) => urls.map(url => [community, url]))
    : (theme.sources[filter] || []).map(url => [filter, url]);
  entries.slice(0, 6).forEach(([community, url], index) => {
    const link = document.createElement('a');
    link.href = url;
    link.target = '_blank';
    link.rel = 'noreferrer';
    link.textContent = 'r/' + community + ' comment ' + (index + 1) + ' ↗';
    sources.append(link);
  });
  if (!entries.length) sources.append(document.createTextNode('None in this sample.'));
  spot.append(kicker, title, body, sources);
}

document.querySelectorAll('.filter').forEach(button => button.addEventListener('click', () => {
  document.querySelector('.filter.active').classList.remove('active');
  button.classList.add('active');
  filter = button.dataset.filter;
  render();
}));
fetch('evidence.json').then(response => {
  if (!response.ok) throw new Error('No reviewed evidence file');
  return response.json();
}).then(data => {
  evidence = data;
  status.textContent = data.coded_threads + ' threads with coded advice · ' + data.coded_comments +
    ' coded comments · updated ' + new Date(data.generated_at).toLocaleDateString() +
    '. Counts are distinct threads, not percentages.';
  render();
}).catch(() => {
  status.textContent = 'Evidence collection is in progress. The chart will appear after Reddit comments are reviewed and coded.';
  bars.textContent = 'No reviewed data published yet.';
  spot.textContent = 'The checklist below is general editorial guidance. It is not presented as a measured result.';
});

const checks = [...document.querySelectorAll('.step input')];
checks.forEach(check => check.addEventListener('change', () => {
  const count = checks.filter(item => item.checked).length;
  document.querySelector('#progressText').textContent = count + ' of 4';
  document.querySelector('#progressBar').style.width = (count * 25) + '%';
}));
const tips = ['Move your clearest solo portrait into slot one.', 'Replace one adjective with a tiny, specific story.', 'Remove the photo most similar to another photo.', 'Add one detail that invites an easy question.', 'Rewrite one negative boundary as a positive preference.'];
let tipIndex = 0;
document.querySelector('#randomTip').addEventListener('click', () => {
  document.querySelector('#tipPop').textContent = '→ ' + tips[tipIndex++ % tips.length];
});
