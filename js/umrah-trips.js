/* سفير الحرمين - برامج العمرة: نفس الشكل الأصلي (صورة + المزيد).
 * يحافظ على الرحلات القديمة من Firestore، ويضيف عروض جوجل المنشورة فقط.
 * لا تعرض هذه الصفحة أسعارًا أو أوصافًا أسفل الصور؛ التفاصيل في details.html.
 */
(function () {
  'use strict';
  const holder = document.querySelector('.new-umrah-trip');
  if (!holder) return;

  const GOOGLE_OFFERS_URL = 'https://script.google.com/macros/s/AKfycbz85MU5YkKwBIcC2d5pH0OaJqptfEOKIo9TSaYAzlUJ9eBg1g23AvCB7-liR-OEUArk/exec';
  const FALLBACK = 'data/umrah-programs-published.json';
  let originalTrips = [], publishedOffers = [], liveReceived = false;

  function safeUrl(value) {
    const url = String(value || '').trim();
    return /^https:\/\/[^\s<>"']+$/i.test(url) ? url : '';
  }

  function photoCard(src, title, url, isGoogle) {
    const col = document.createElement('div');
    col.className = 'col p-lg-4 py-3';
    const img = document.createElement('img');
    img.className = 'rounded-4 shadow';
    img.alt = title || 'برنامج عمرة';
    img.loading = 'lazy';
    img.decoding = 'async';
    img.style.width = '100%';
    img.style.aspectRatio = '4 / 5';
    img.style.background = '#f8f5ee';
    img.style.objectFit = 'contain';
    img.style.display = 'block';
    if (isGoogle) {
      img.src = safeUrl(src) || './img/umrah-trips.png';
    } else {
      img.src = './img/umrah-imgs/' + encodeURIComponent(String(src || '').replace(/^.*[\\/]/, ''));
    }
    img.onerror = function () {
      if (!img.dataset.fallback && !isGoogle) {
        // The copied GitHub repo may be missing some legacy posters still on the original site.
        img.dataset.fallback = 'original-domain';
        img.src = 'https://safiralharamain.com/img/umrah-imgs/' +
          encodeURIComponent(String(src || '').replace(/^.*[\\/]/, ''));
        return;
      }
      if (img.dataset.fallback !== 'generic') {
        img.dataset.fallback = 'generic';
        img.src = './img/umrah-trips.png';
      }
    };
    col.appendChild(img);

    const more = document.createElement('button');
    more.type = 'button';
    more.className = 'btn-primary border-0 text-regular fs-5 mt-3 mx-auto user-select-none';
    more.style.display = 'flex';
    more.style.alignItems = 'center';
    more.style.justifyContent = 'center';
    more.style.cursor = 'pointer';
    const label = document.createElement('span');
    label.textContent = 'المزيــد';
    const arrow = document.createElement('img');
    arrow.className = 'ms-3';
    arrow.src = './img/icons/arrow-link.svg';
    arrow.alt = '';
    arrow.width = 25;
    more.append(label, arrow);
    more.addEventListener('click', function () { window.location.href = url; });
    col.appendChild(more);
    return col;
  }

  function render() {
    holder.replaceChildren();
    publishedOffers.slice().sort(function(a,b){
      return (Date.parse(b.created_at)||0)-(Date.parse(a.created_at)||0);
    }).forEach(function (trip) {
      if (!trip || !trip.id || trip.status !== 'منشور') return;
      holder.appendChild(photoCard(
        trip.image_url, trip.title,
        'details.html?offer=' + encodeURIComponent(trip.id), true
      ));
    });
    originalTrips.forEach(function (trip) {
      if (!trip || !trip.id) return;
      holder.appendChild(photoCard(
        trip.imgs, trip.tripTitle || 'برنامج عمرة',
        'details.html?id=' + encodeURIComponent(trip.id), false
      ));
    });
    if (!holder.children.length) {
      const text = document.createElement('p');
      text.className = 'text-center text-gray text-regular w-100 py-5';
      text.textContent = 'لا توجد برامج عمرة منشورة حاليًا.';
      holder.appendChild(text);
    }
  }

  async function loadOriginalTrips() {
    try {
      if (typeof db === 'undefined') return;
      const query = await db.collection('trips').where('category', '==', 'umrah-2').get();
      const result = [];
      query.forEach(function (doc) { result.push(Object.assign({ id: doc.id }, doc.data())); });
      result.sort(function (a, b) { return Number(a.sort || 0) - Number(b.sort || 0); });
      originalTrips = result;
    } catch (err) {
      console.warn('Original Umrah trip service unavailable:', err);
    }
    render();
  }

  async function loadBackup() {
    try {
      const response = await fetch(FALLBACK, { cache: 'no-store' });
      if (!response.ok) throw new Error('Backup not available');
      const data = await response.json();
      if (liveReceived) return;
      publishedOffers = Array.isArray(data.offers) ? data.offers : [];
    } catch (err) {
      console.warn('Published Umrah backup unavailable:', err);
    }
    render();
  }

  // Called only by the read-only published-offers Google Apps Script endpoint.
  window.safirUmrahReceive = function (payload) {
    if (!payload || payload.ok !== true || !Array.isArray(payload.offers)) return;
    liveReceived = true;
    publishedOffers = payload.offers;
    render();
  };

  function loadPublishedLive() {
    const script = document.createElement('script');
    script.async = true;
    script.src = GOOGLE_OFFERS_URL + '?format=jsonp&callback=safirUmrahReceive&t=' + Date.now();
    script.onerror = function () { script.remove(); };
    document.head.appendChild(script);
  }

  render();
  loadOriginalTrips();
  loadBackup();
  loadPublishedLive();
})();