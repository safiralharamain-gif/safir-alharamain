(() => {
  const DATA_URL = './data/site-content.json?v=' + Date.now();

  function parseYouTubeTime(value=''){
    if(!value) return 0;
    if(/^\d+$/.test(value)) return Number(value);
    let total = 0;
    const h = value.match(/(\d+)h/);
    const m = value.match(/(\d+)m/);
    const s = value.match(/(\d+)s/);
    if(h) total += Number(h[1]) * 3600;
    if(m) total += Number(m[1]) * 60;
    if(s) total += Number(s[1]);
    return total;
  }

  function youtubeInfo(url=''){
    try{
      const u = new URL(url);
      let id = '';
      if(u.hostname.includes('youtu.be')) id = u.pathname.split('/').filter(Boolean)[0] || '';
      else if(u.pathname.includes('/shorts/')) id = u.pathname.split('/shorts/')[1].split('/')[0];
      else if(u.pathname.includes('/embed/')) id = u.pathname.split('/embed/')[1].split('/')[0];
      else id = u.searchParams.get('v') || '';

      const start = parseYouTubeTime(u.searchParams.get('t') || u.searchParams.get('start') || '');
      return {id,start};
    }catch(e){
      const m = url.match(/(?:youtu\.be\/|youtube\.com\/(?:watch\?v=|shorts\/|embed\/))([A-Za-z0-9_-]{6,})/);
      const tm = url.match(/[?&](?:t|start)=([^&]+)/);
      return {id:m ? m[1] : '', start:tm ? parseYouTubeTime(tm[1]) : 0};
    }
  }

  function videoHtml(url){
    const info = youtubeInfo(url);
    if(!info.id) return '';
    const params = ['rel=0','modestbranding=1'];
    if(info.start > 0) params.push('start='+info.start);
    const embed = 'https://www.youtube.com/embed/'+info.id+'?'+params.join('&');
    return '<div class="safir-video-wrap"><div class="safir-video"><iframe loading="lazy" src="'+embed+'" title="فيديو سفير الحرمين" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe></div><a class="safir-youtube-fallback" href="'+esc(url)+'" target="_blank" rel="noopener">إذا لم يعمل الفيديو اضغط هنا لفتحه على YouTube</a></div>';
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