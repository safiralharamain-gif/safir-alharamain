(() => {
  const DATA_URL = './data/site-content.json?v=' + Date.now();

  function youtubeId(url=''){
    try{
      const u = new URL(url);
      if(u.hostname.includes('youtu.be')) return u.pathname.split('/').filter(Boolean)[0] || '';
      if(u.pathname.includes('/shorts/')) return u.pathname.split('/shorts/')[1].split('/')[0];
      if(u.pathname.includes('/embed/')) return u.pathname.split('/embed/')[1].split('/')[0];
      return u.searchParams.get('v') || '';
    }catch(e){
      const m = url.match(/(?:youtu\.be\/|youtube\.com\/(?:watch\?v=|shorts\/|embed\/))([A-Za-z0-9_-]{6,})/);
      return m ? m[1] : '';
    }
  }

  function videoHtml(url){
    const id = youtubeId(url);
    if(!id) return '';
    return '<div class="safir-video"><iframe loading="lazy" src="https://www.youtube-nocookie.com/embed/'+id+'" title="فيديو سفير الحرمين" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe></div>';
  }

  function esc(s=''){
    return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
  }

  function imgHtml(src, alt=''){
    if(!src) return '';
    return '<img loading="lazy" src="'+esc(src)+'" alt="'+esc(alt)+'" data-safir-lightbox>';
  }

  function renderGuide(prefix, guide){
    if(!guide) return;
    const title = document.querySelector('[data-'+prefix+'-title]');
    const subtitle = document.querySelector('[data-'+prefix+'-subtitle]');
    const body = document.querySelector('[data-'+prefix+'-body]');
    const images = document.querySelector('[data-'+prefix+'-images]');
    const videos = document.querySelector('[data-'+prefix+'-videos]');
    if(title) title.textContent = guide.title || '';
    if(subtitle) subtitle.textContent = guide.subtitle || '';
    if(body) body.textContent = guide.body || '';
    if(images){
      const list = (guide.images || []).filter(Boolean);
      images.innerHTML = list.map(x => imgHtml(x, guide.title)).join('');
      images.style.display = list.length ? 'grid' : 'none';
    }
    if(videos){
      const html = (guide.videos || []).map(videoHtml).filter(Boolean).join('');
      videos.innerHTML = html;
      videos.style.display = html ? 'grid' : 'none';
    }
  }

  function renderPastTrips(trips){
    const el = document.querySelector('[data-past-trips]');
    if(!el) return;
    if(!Array.isArray(trips) || !trips.length){
      el.innerHTML = '<div class="safir-empty">سيتم إضافة صور وفيديوهات رحلاتنا السابقة هنا من لوحة الإدارة.</div>';
      return;
    }
    el.innerHTML = trips.filter(t => t && t.visible !== false).map(t => {
      const images = (t.images || []).filter(Boolean);
      const cover = t.cover || images[0] || './img/web-img.png';
      const videos = (t.videos || []).map(videoHtml).filter(Boolean).join('');
      return '<article class="safir-trip-card">'+
        imgHtml(cover, t.title || 'من رحلاتنا السابقة').replace('<img ','<img class="safir-trip-cover" ')+
        '<div class="safir-trip-body">'+
          '<div class="safir-trip-date">'+esc(t.date || '')+'</div>'+
          '<h3>'+esc(t.title || 'رحلة عمرة')+'</h3>'+
          '<p>'+esc(t.description || '')+'</p>'+
          (images.length ? '<div class="safir-trip-gallery">'+images.slice(0,6).map(x => imgHtml(x,t.title)).join('')+'</div>' : '')+
          (videos ? '<div class="safir-video-grid" style="grid-template-columns:1fr;margin-top:1rem">'+videos+'</div>' : '')+
        '</div></article>';
    }).join('');
  }

  function bindLightbox(){
    const lb = document.querySelector('.safir-lightbox');
    const lbImg = lb && lb.querySelector('img');
    if(!lb || !lbImg) return;
    document.addEventListener('click', e => {
      const img = e.target.closest('[data-safir-lightbox]');
      if(img){
        lbImg.src = img.src;
        lb.classList.add('open');
      }
      if(e.target === lb || e.target.closest('[data-lightbox-close]')) lb.classList.remove('open');
    });
    document.addEventListener('keydown', e => { if(e.key === 'Escape') lb.classList.remove('open'); });
  }

  fetch(DATA_URL,{cache:'no-store'})
    .then(r => r.ok ? r.json() : Promise.reject(new Error('content fetch failed')))
    .then(data => {
      renderGuide('umrah', data.umrahGuide);
      renderGuide('hajj', data.hajjGuide);
      renderPastTrips(data.pastTrips || []);
    })
    .catch(() => {
      renderPastTrips([]);
    })
    .finally(bindLightbox);
})();