/* Safir Al-Haramain: shared photo-only offers renderer for all commercial sections.
 * Keeps the existing website markup. Only published offers for this section are displayed.
 * Requires the owner to publish cms-v3/OffersPublic.gs as a new version of the current read-only deployment.
 */
(function(){
 'use strict';
 const sections=Array.from(document.querySelectorAll('[data-safir-offers]'),function(host){
   return {
     host:host,
     category:host.getAttribute('data-safir-offers'),
     container:host.querySelector('[data-safir-grid]'),
     status:host.querySelector('[data-safir-status]'),
     limit:Number(host.getAttribute('data-safir-limit'))
   };
 }).filter(function(section){return section.category&&section.container});
 if(!sections.length)return;
 const FEED='https://script.google.com/macros/s/AKfycbz85MU5YkKwBIcC2d5pH0OaJqptfEOKIo9TSaYAzlUJ9eBg1g23AvCB7-liR-OEUArk/exec';
 function validImage(s){return /^https:\/\/[^\s"'<>]+$/i.test(String(s||''))?String(s):''}
 function makeCard(offer){
   const col=document.createElement('div');
   col.className='col p-lg-4 py-3';
   const poster=document.createElement('img');
   poster.className='rounded-4 shadow';
   poster.alt=offer.title||'صورة عرض سفير الحرمين';
   poster.loading='lazy';
   poster.style.cssText='display:block;width:100%;aspect-ratio:4/5;object-fit:contain;background:#f8f5ee';
   poster.src=validImage(offer.image_url)||'./img/umrah-trips.png';
   poster.onerror=function(){
     if(poster.dataset.backup)return;
     poster.dataset.backup='1';poster.src='./img/umrah-trips.png';
   };
   col.appendChild(poster);
   const more=document.createElement('button');
   more.type='button';
   more.className='btn-primary border-0 text-regular fs-5 mt-3 mx-auto user-select-none';
   more.style.cssText='display:flex;align-items:center;justify-content:center;cursor:pointer';
   const name=document.createElement('span');name.textContent='المزيــد';
   const arrow=document.createElement('img');
   arrow.className='ms-3';arrow.src='./img/icons/arrow-link.svg';arrow.alt='';arrow.width=25;
   more.append(name,arrow);
   more.addEventListener('click',function(){window.location.href='details.html?offer='+encodeURIComponent(offer.id)});
   col.appendChild(more);
   return col;
 }
 function showError(){
   sections.forEach(function(section){
     if(section.status)section.status.textContent='تعذّر تحميل الرحلات الآن. تقدر تفتح صفحة برامج العمرة من الرابط أدناه.';
     else section.host.hidden=true;
   });
 }
 window.safirSiteOffersReceive=function(payload){
   if(!payload||payload.ok!==true||!Array.isArray(payload.offers)){
     showError();
     return;
   }
   const published=payload.offers.filter(function(offer){
     return offer&&offer.id&&offer.status==='منشور';
   }).sort(function(a,b){
     return (Date.parse(b.created_at)||0)-(Date.parse(a.created_at)||0);
   });
   sections.forEach(function(section){
     const offers=published.filter(function(offer){return offer.category===section.category});
     const visibleOffers=section.limit>0?offers.slice(0,section.limit):offers;
     section.container.replaceChildren();
     visibleOffers.forEach(function(offer){section.container.appendChild(makeCard(offer))});
     if(section.status){
       section.status.hidden=visibleOffers.length>0;
       section.status.textContent=visibleOffers.length?'':'لا توجد رحلات عمرة منشورة حاليًا.';
     }else{
       section.host.hidden=!visibleOffers.length;
     }
   });
 };
 const script=document.createElement('script');
 script.async=true;
 script.src=FEED+'?format=jsonp&callback=safirSiteOffersReceive&t='+Date.now();
 script.onerror=function(){script.remove();showError()};
 document.head.append(script);
})();
