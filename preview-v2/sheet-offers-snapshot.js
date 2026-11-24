(()=>{
'use strict';
// This is a dated fallback preview, NOT the automatic live publishing channel.
const holder=document.getElementById('safir-sheets-offers');
if(!holder)return;
function el(tag,cls,txt){const e=document.createElement(tag);if(cls)e.className=cls;if(txt!==undefined)e.textContent=txt;return e;}
function text(v){return String(v==null?'':v);}
const source='preview-v2/data/last-published-offers.json';
fetch(source,{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('missing snapshot');return r.json()}).then(data=>{
 const offers=Array.isArray(data.offers)?data.offers:[];holder.replaceChildren();
 if(!offers.length){holder.append(el('p','safir-offers-note','لا توجد عروض منشورة في آخر نسخة تم التحقق منها.'));return;}
 const grid=el('div','safir-sheets-grid');
 for(const x of offers){
  const card=el('article','safir-sheets-card');
  const imageBox=el('div','safir-sheets-photo');
  const img=el('img');img.loading='lazy';img.alt='صورة '+text(x.title);
  if(/^https:\/\/[^\s<>"]+$/i.test(text(x.image_url))){
    img.src=x.image_url;
    img.onerror=()=>{img.remove();imageBox.textContent='صورة العرض غير متاحة للعرض العام حاليًا';imageBox.classList.add('safir-photo-unavailable')};
    imageBox.append(img);
  }else imageBox.textContent='صورة العرض قيد التجهيز';
  const info=el('div','safir-sheets-body');
  const title=el('h3','',x.title||'برنامج عمرة');info.append(title);
  info.append(el('p','safir-sheets-price',Number(x.price).toLocaleString('en-US')+' جنيه'));
  const meta=[x.departure_date?'تاريخ السفر: '+x.departure_date:'',x.duration_days?'المدة: '+x.duration_days+' يوم':'',x.hotel?'الفندق: '+x.hotel:''].filter(Boolean).join(' • ');
  info.append(el('p','safir-sheets-meta',meta));
  if(x.description)info.append(el('p','safir-sheets-meta',x.description));
  const link=el('a','btn btn-secondary rounded-5 px-4','استفسر عن العرض');
  link.href='https://wa.me/201150337383?text='+encodeURIComponent('السلام عليكم، أريد الاستفسار عن '+text(x.title));
  link.target='_blank';link.rel='noopener noreferrer';info.append(link);
  card.append(imageBox,info);grid.append(card);
 }
 holder.append(grid);
 const note=el('p','safir-offers-note','آخر نسخة منشورة تمت مزامنتها بتاريخ '+text(data.syncedAt||'غير محدد')+' — تحديثات العروض التالية تحتاج تفعيل النشر المباشر من جوجل.');
 holder.append(note);
}).catch(()=>{holder.textContent='تعذر تحميل نسخة العروض المنشورة. افتح رابط عروض جوجل للتأكد من آخر التحديثات.'});
})();
