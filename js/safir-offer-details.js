/* Google Sheets Umrah offer details using the site's EXISTING details.html page & design.
 * Original Firestore detailsPage.js remains unchanged for old trips.
 */
(function () {
  'use strict';
  const offerId = new URLSearchParams(window.location.search).get('offer');
  if (!offerId) return;
  const container = document.querySelector('.details-container');
  if (!container) return;
  const URL_BACKUP = 'data/umrah-programs-published.json';
  const URL_LIVE = 'https://script.google.com/macros/s/AKfycbz85MU5YkKwBIcC2d5pH0OaJqptfEOKIo9TSaYAzlUJ9eBg1g23AvCB7-liR-OEUArk/exec';
  const URL_BOOKING = 'https://script.google.com/macros/s/AKfycbzDnlNzZLnZ9d32pqQ9mXW8DF-BpoY-YD8aCv1yV-SuDcWN3Z2SqwKwwJPSbDIkXwAm/exec';
  const sections={
    umrah:{name:'عمرة',page:'umrah-booking.html'},
    hajj:{name:'حج',page:'hajj-trips.html'},
    internal:{name:'رحلة داخلية',page:'travel-trips.html'},
    hotel:{name:'فنادق',page:'hotel-booking.html'},
    flight:{name:'طيران',page:'flight-booking.html'},
    visa:{name:'تأشيرات',page:'visa.html'},
    transport:{name:'نقل وليموزين',page:'transport.html'},
    barcode:{name:'باركود',page:'barcode.html'},
    general:{name:'عرض سفير الحرمين',page:'index.html'}
  };
  let currentOffer = null, liveFound = false;

  function node(name, className, value) {
    const n = document.createElement(name);
    if (className) n.className = className;
    if (value !== undefined && value !== null) n.textContent = String(value);
    return n;
  }
  function url(v) { const s = String(v || '').trim(); return /^https:\/\/[^\s<>"']+$/i.test(s) ? s : ''; }
  function block(parent, child) { parent.appendChild(child); return child; }
  function sectionHeader(title) { return node('h3', 'fs-5 mb-3', title); }

  function makeTable(rows) {
    const area = node('div', 'program-details mx-auto mt-5');
    area.style.maxWidth = '900px';
    area.append(sectionHeader('تفاصيل البرنامج:'));
    const table = node('table', 'table table-striped table-bordered rounded-4 overflow-hidden mb-4');
    const body = node('tbody');
    rows.forEach(function (row) {
      if (row[1] === undefined || row[1] === null || String(row[1]).trim() === '') return;
      const tr = node('tr');
      tr.append(node('td', 'table-row', row[0]), node('td', 'table-row', row[1]));
      body.appendChild(tr);
    });
    table.append(body); area.append(table); return area;
  }

  function render(o) {
    if (!o || o.status !== 'منشور') return;
    currentOffer = o;
    const category=sections[o.category]||sections.umrah;
    const tripSection=(o.category==='umrah'||o.category==='hajj');
    document.title = (o.title || 'تفاصيل العرض') + ' | سفير الحرمين';
    container.replaceChildren();
    const root = node('div', 'container mx-auto px-3');root.style.maxWidth = '1000px';
    const h = node('h1', 'fs-2 text-center lh-lg mb-0', o.title || 'تفاصيل العرض');
    h.style.marginTop = '10rem';root.append(h);
    const imageBox = node('div', 'details-imgs w-100 mx-auto rounded-5 overflow-hidden shadow');
    const poster = node('img', 'w-100');poster.alt = o.title || 'صورة البرنامج';
    poster.loading = 'eager';poster.style.objectFit = 'contain';poster.style.maxHeight='1000px';
    poster.style.height='auto';poster.style.display='block';poster.style.background='#f8f5ee';
    poster.src = url(o.image_url) || './img/umrah-trips.png';
    poster.onerror = function () { poster.onerror = null; poster.src = './img/umrah-trips.png'; };
    imageBox.append(poster);root.append(imageBox);
    if (o.description)root.append(node('p', 'fs-6 text-center lh-lg mt-3', o.description));
    const x = o.extras || {};
    const cost = Number(o.price);
    const roomPrice = function (value) {
      const amount = String(value ?? '').trim();
      return amount ? amount + ' جنيه مصري' : '';
    };
    const table = makeTable([
      ['المستوى', x.level],
      [tripSection?'تاريخ الرحلة':'تاريخ العرض أو الخدمة', o.departure_date],
      [tripSection?'مدة الرحلة':'المدة', x.durationLabel || (o.duration_days ? o.duration_days + ' يوم' : '')],
      ['تاريخ العودة', x.returnDate],
      ['مسار الرحلة', x.itinerary],
      ['شركة الطيران', x.airline],
      [tripSection?'فندق مكة':'الفندق أو المكان', o.hotel],
      [tripSection?'فندق المدينة':'موقع آخر', x.madinahHotel],
      ['الطيران والانتقالات', x.transport],
      ['سعر الخماسي', roomPrice(x.fivePrice)],
      ['سعر الرباعي', roomPrice(x.quadruplePrice)],
      ['سعر الثلاثي', roomPrice(x.triplePrice)],
      ['سعر الثنائي', roomPrice(x.binaryPrice)],
      ['سعر الطفل', roomPrice(x.childPrice)],
      ['سعر الرضيع', roomPrice(x.infantPrice)],
      ['شركة السياحة', x.agency],
      ['سعر العرض', Number.isFinite(cost) && cost > 0 ? cost.toLocaleString('ar-EG') + ' جنيه مصري' : 'يُحدد عند الاستفسار']
    ]);
    root.append(table);
    if (x.notes) {
      const notes = node('div', 'trip-notes mb-4 mx-auto');
      notes.style.maxWidth = '900px';
      notes.append(sectionHeader('ملاحظات وشروط العرض:'));
      String(x.notes).split(/\r?\n/).map(line => line.trim()).filter(Boolean)
        .forEach(line => notes.append(node('p', 'lh-lg mb-2', line)));
      root.append(notes);
    }
    if (x.includes) {
      const inc=node('div','program-includes mt-5 mb-3 mx-auto px-2');inc.style.maxWidth='900px';
      inc.append(sectionHeader('البرنامج يشمل:'));
      const ul=node('ul','mt-3');
      String(x.includes).split(/\r?\n/).map(v=>v.trim()).filter(Boolean).forEach(v=>ul.append(node('li','pro-item lh-lg',v)));
      inc.append(ul);root.append(inc);
    }
    if (x.excludes) {
      const exc=node('div','trip-notes mt-5 mb-3 mx-auto px-2');exc.style.maxWidth='900px';
      exc.append(sectionHeader('البرنامج لا يشمل:'),node('p','lh-lg mb-0',x.excludes));root.append(exc);
    }
    const gallery=(o.gallery||[]).filter(v=>url(v&&v.url)&&v.url!==o.image_url);
    if(gallery.length){
      const wrap=node('div','mx-auto mt-5');wrap.style.maxWidth='900px';
      wrap.append(sectionHeader('صور أخرى من العرض:'));
      const photos=node('div');photos.style.cssText='display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px';
      gallery.slice(0,12).forEach(function (pic) {
        const im=node('img','rounded-4 shadow');im.src=url(pic.url);im.alt=pic.name||'صورة رحلة عمرة';
        im.loading='lazy';im.style.cssText='width:100%;height:220px;object-fit:contain;background:#f6f2e8';
        photos.append(im);
      });
      wrap.append(photos);root.append(wrap);
    }
    if(tripSection){
    const docs=node('div','required-doc mt-5 mb-5 mx-auto px-2');docs.style.maxWidth='900px';
    docs.append(sectionHeader('الأوراق والمستندات المطلوبة:'));
    const list=node('ul','mt-3');
    ['جواز سفر صالح لمدة لا تقل عن 6 شهور على الأقل.',
     'شهادة صحية خاصة بالحج والعمرة.',
     'عدد ( 2 ) صور شخصية حديثة خلفية بيضاء.',
     'استخراج تصريح سفر لمن هم في سن التجنيد.'].forEach(t=>list.append(node('li','pro-item lh-lg',t)));
    docs.append(list,node('p','mt-5','* تطبق الشروط والأحكام.'),
      node('p','text-bold text-secondary lh-lg mt-3','للمزيد من التفاصيل يرجى التواصل معنا لنتمكن من خدمتكم بشكل أفضل.'));
    root.append(docs);container.append(root);

    }

    const bookingSection=node('section','section bg-secondary');
    const center=node('div','container');
    const box=node('div','booking-form bg-white rounded-5 shadow p-3 p-md-5 mx-auto');
    box.style.maxWidth='900px';
    box.append(node('h3','booking-title fs-1 text-center text-secondary mx-auto mt-2 mb-5',
       o.category==='umrah'?'حجـز رحلـة عمـرة':'تفاصيل الحجز والاستفسار'));
    if(o.category==='umrah'){
      box.append(node('p','text-regular text-center text-gray lh-lg',
        'ابعت طلبك على واتساب. فريق سفير الحرمين هيتواصل معاك لتأكيد الحجز.'));
      const accountForm=node('details','mt-4');
      accountForm.append(node('summary','text-bold','نموذج الحجز لحساب سفير الحرمين'));
      const iframe=node('iframe');
      const params=new URLSearchParams({tripName:o.title||'',service:'عمرة',date:o.departure_date||''});
      iframe.src=URL_BOOKING+'?'+params.toString();
      iframe.title='نموذج حجز '+(o.title||'العمرة');
      iframe.loading='lazy';
      iframe.style.cssText='display:block;border:0;width:100%;height:1420px;border-radius:12px;background:#faf8f3';
      accountForm.addEventListener('toggle',function(){
        if(accountForm.open&&!iframe.isConnected)accountForm.append(iframe);
      });
      box.append(accountForm);
      const fallback=node('p','text-center mt-3');
      const a=node('a','btn btn-secondary rounded-4 px-4 py-3','فتح استمارة الحجز في صفحة مستقلة');
      a.href=iframe.src;a.target='_blank';a.rel='noopener noreferrer';
      fallback.append(a);accountForm.append(fallback);
    }else{
      box.append(node('p','text-regular text-center text-gray lh-lg',
        'للحجز أو الاستفسار عن هذا العرض، تواصل مع فريق سفير الحرمين أو افتح صفحة الخدمة.'));
      const go=node('p','text-center mt-3');
      const a=node('a','btn btn-secondary rounded-4 px-4 py-3','فتح صفحة '+category.name);
      a.href=category.page;go.append(a);box.append(go);
    }
    const wa=node('p','text-center mt-3');
    const contact=node('a','btn btn-secondary rounded-4 px-4 py-3',o.category==='umrah'?'اطلب الحجز على واتساب':'الاستفسار عبر واتساب');
    contact.href='https://wa.me/201150337383?text='+encodeURIComponent((o.category==='umrah'?'السلام عليكم، أريد حجز برنامج: ':'السلام عليكم، أريد تفاصيل برنامج: ')+(o.title||category.name)+(o.departure_date?'\nتاريخ الرحلة: '+o.departure_date:''));
    contact.target='_blank';contact.rel='noopener noreferrer';wa.append(contact);
    if(o.category==='umrah')box.insertBefore(wa,box.querySelector('details'));
    else box.append(wa);
    center.append(box);bookingSection.append(center);container.append(bookingSection);
  }

  function find(o) {
    const offers=Array.isArray(o)?o:Array.isArray(o&&o.offers)?o.offers:[];
    return offers.find(x=>x && x.id===offerId && x.status==='منشور');
  }
  function showMissing() {
    if (currentOffer) return;
    container.replaceChildren();
    const msg=node('div','container text-center text-regular text-gray');
    msg.style.padding='170px 15px 65px';
    msg.append(node('h2','mb-3','تعذر تحميل تفاصيل العرض'));
    const p=node('p','','ارجع إلى الموقع أو القسم المطلوب وحاول مرة أخرى.');msg.append(p);
    const a=node('a','btn btn-secondary rounded-4 px-4','العودة للرئيسية');
    a.href='index.html';msg.append(a);container.append(msg);
  }

  container.append(node('p','text-center text-gray text-regular','جارٍ تحميل تفاصيل العرض...'));
  window.safirSiteOffersReceive=function(payload){
    if(payload&&payload.ok===true&&Array.isArray(payload.offers)){
      const found=find(payload);
      if(found){liveFound=true;render(found);}
      else if(!currentOffer)showMissing();
    }
  };
  fetch(URL_BACKUP,{cache:'no-store'}).then(r=>r.ok?r.json():Promise.reject()).then(data=>{
    if(!liveFound){const offer=find(data);if(offer)render(offer);}
  }).catch(()=>{});
  const script=document.createElement('script');script.async=true;
  script.src=URL_LIVE+'?format=jsonp&callback=safirSiteOffersReceive&t='+Date.now();
  script.onerror=function(){script.remove();if(!currentOffer)showMissing()};
  document.head.append(script);
  setTimeout(showMissing,5500);
})();