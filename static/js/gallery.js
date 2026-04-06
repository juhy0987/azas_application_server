async function fetchProjects() {
  const response = await fetch('/api/projects');
  if (!response.ok) {
    throw new Error('Failed to fetch projects');
  }
  return response.json();
}

function notionEmbedUrl(url) {
  if (!url) {
    return '';
  }

  const encoded = encodeURIComponent(url);
  return `https://notion.site/embed/${encoded}`;
}

function createProjectCard(project) {
  const template = document.getElementById('project-card-template');
  const fragment = template.content.cloneNode(true);
  const card = fragment.querySelector('.project-card');

  fragment.querySelector('.project-title').textContent = project.title;
  fragment.querySelector('.project-subtitle').textContent = project.subtitle || '';

  const markdownBody = fragment.querySelector('.markdown-body');
  markdownBody.innerHTML = marked.parse(project.markdown || '');

  const image = fragment.querySelector('.project-image');
  if (project.image_url) {
    image.src = project.image_url;
  } else {
    image.style.display = 'none';
  }

  const notionFrame = fragment.querySelector('.notion-frame');
  if (project.notion_url) {
    notionFrame.src = notionEmbedUrl(project.notion_url);
  } else {
    notionFrame.style.display = 'none';
  }

  const toggleBtn = fragment.querySelector('.toggle-btn');
  toggleBtn.addEventListener('click', (event) => {
    event.stopPropagation();
    card.classList.toggle('is-flipped');
    toggleBtn.textContent = card.classList.contains('is-flipped') ? 'Back to Front' : 'View Detail';
  });

  card.addEventListener('click', () => {
    card.classList.toggle('is-flipped');
    toggleBtn.textContent = card.classList.contains('is-flipped') ? 'Back to Front' : 'View Detail';
  });

  return fragment;
}

async function initGallery() {
  const gallery = document.getElementById('gallery');

  try {
    const projects = await fetchProjects();
    projects.forEach((project) => {
      gallery.appendChild(createProjectCard(project));
    });
  } catch (error) {
    gallery.innerHTML = `<p>전시 데이터를 불러오지 못했습니다: ${error.message}</p>`;
  }
}

window.addEventListener('DOMContentLoaded', initGallery);
