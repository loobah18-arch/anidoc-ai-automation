// AniDoc AI Studio Web Dashboard Client Logic

let currentProject = null;

document.addEventListener('DOMContentLoaded', () => {
  setupTabs();
  setupEventListeners();
});

function setupTabs() {
  const tabButtons = document.querySelectorAll('.tab-btn');
  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      tabButtons.forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

      btn.classList.add('active');
      const target = btn.getAttribute('data-tab');
      const targetContent = document.getElementById(target);
      if (targetContent) {
        targetContent.classList.add('active');
      }
    });
  });
}

function setupEventListeners() {
  const btnTopics = document.getElementById('btn-generate-topics');
  const btnRunPipeline = document.getElementById('btn-run-pipeline');
  const btnRenderMedia = document.getElementById('btn-render-media');

  btnTopics.addEventListener('click', handleGenerateTopics);
  btnRunPipeline.addEventListener('click', handleRunPipeline);
  btnRenderMedia.addEventListener('click', handleRenderMedia);
}

async function handleGenerateTopics() {
  const statusInd = document.querySelector('.status-indicator');
  const lang = document.getElementById('language-select').value;
  const out = document.getElementById('topics-output');

  statusInd.className = 'status-indicator busy';
  statusInd.textContent = 'GENERATING TOPICS...';
  out.textContent = 'Contacting AI Engine for 10 high-retention topics...';
  switchTab('tab-topics');

  try {
    const res = await fetch('/api/generate-topics', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ language: lang })
    });
    const data = await res.json();
    if (data.status === 'success') {
      out.textContent = data.topics;
    } else {
      out.textContent = 'Error: ' + JSON.stringify(data);
    }
  } catch (e) {
    out.textContent = 'Network or Server Error: ' + e.message;
  } finally {
    statusInd.className = 'status-indicator ready';
    statusInd.textContent = 'READY';
  }
}

async function handleRunPipeline() {
  const statusInd = document.querySelector('.status-indicator');
  const lang = document.getElementById('language-select').value;
  const topic = document.getElementById('topic-input').value;

  statusInd.className = 'status-indicator busy';
  statusInd.textContent = 'RUNNING 6-STATE PIPELINE...';
  switchTab('tab-script');
  document.getElementById('script-output').textContent = 'Generating full Style DNA analysis and clean voiceover script...';

  try {
    const res = await fetch('/api/run-pipeline', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic, language: lang })
    });
    const data = await res.json();
    if (data.status === 'success') {
      currentProject = data.project_name;
      document.getElementById('script-output').textContent = data.script;
      document.getElementById('images-output').textContent = data.image_prompts;
      document.getElementById('motion-output').textContent = data.motion_prompts;
      document.getElementById('thumbs-output').textContent = data.thumbnail_concepts;
      document.getElementById('seo-output').textContent = data.seo_package;
    } else {
      alert('Pipeline execution failed: ' + JSON.stringify(data));
    }
  } catch (e) {
    alert('Error running pipeline: ' + e.message);
  } finally {
    statusInd.className = 'status-indicator ready';
    statusInd.textContent = 'READY';
  }
}

async function handleRenderMedia() {
  const statusInd = document.querySelector('.status-indicator');
  statusInd.className = 'status-indicator busy';
  statusInd.textContent = 'RENDERING 1080P VIDEO & AUDIO...';
  switchTab('tab-media');

  const mediaArea = document.getElementById('media-preview-area');
  mediaArea.innerHTML = '<div class="placeholder-box"><p>Rendering voiceover, Flux 2D frames, Ken Burns animation & subtitles...</p></div>';

  try {
    const res = await fetch('/api/render-media', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_name: currentProject, max_images: 4 })
    });
    const data = await res.json();
    if (data.status === 'success') {
      const m = data.media;
      mediaArea.innerHTML = `
        <div class="media-card">
          <h4>Final 1080p Documentary Video</h4>
          <video controls src="/output/${currentProject}/final_documentary.mp4"></video>
          <a class="btn btn-secondary" href="/output/${currentProject}/final_documentary.mp4" download>Download Video (.mp4)</a>
        </div>
        <div class="media-card">
          <h4>Viral High-CTR Thumbnail</h4>
          <img src="/output/${currentProject}/thumbnail.jpg" alt="Thumbnail">
          <a class="btn btn-secondary" href="/output/${currentProject}/thumbnail.jpg" download>Download Thumbnail</a>
        </div>
        <div class="media-card">
          <h4>Voiceover Narration Track</h4>
          <audio controls src="/output/${currentProject}/audio/voiceover.mp3" style="width:100%;margin-top:10px;"></audio>
          <a class="btn btn-secondary" href="/output/${currentProject}/audio/voiceover.mp3" download style="margin-top:10px;">Download Audio (.mp3)</a>
        </div>
      `;
    } else {
      alert('Rendering failed: ' + JSON.stringify(data));
    }
  } catch (e) {
    alert('Rendering error: ' + e.message);
  } finally {
    statusInd.className = 'status-indicator ready';
    statusInd.textContent = 'READY';
  }
}

function switchTab(tabId) {
  document.querySelectorAll('.tab-btn').forEach(b => {
    if (b.getAttribute('data-tab') === tabId) b.classList.add('active');
    else b.classList.remove('active');
  });
  document.querySelectorAll('.tab-content').forEach(c => {
    if (c.id === tabId) c.classList.add('active');
    else c.classList.remove('active');
  });
}

function copyText(elementId) {
  const el = document.getElementById(elementId);
  const text = el.innerText || el.textContent;
  navigator.clipboard.writeText(text).then(() => {
    alert('Copied to clipboard!');
  }).catch(err => {
    alert('Failed to copy: ' + err);
  });
}
