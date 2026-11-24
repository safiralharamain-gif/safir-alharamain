/* Safir Al-Haramain: shared photo-only offers renderer for all commercial sections.
 * Keeps the existing website markup. Only published offers for this section are displayed.
 * Requires the owner to publish cms-v3/OffersPublic.gs as a new version of the current read-only deployment.
 */
(function(){
 'use strict';
 const host=document.querySelector('[data-safir-offers]');
 if(!host)return;
 const category=host.getAttribute('data-safir-offers')||'';
 const container=host.querySelector('[data-safir-grid]');
 const FEED='https://script.google.com/macros/s/AKfycbz85MU5YkKwBIcC2d5pH0OaJqptfEOKIo9TSaYAzlUJ9eBg1g23AvCB7-liR-OEUArk/exec';
 if(!container||!category)return;
 function validImage(s){return /^https:\/\/[^\s"'<>]+$/i.test(String(s||''))?String(s):''}
 function makeCard(offer){
   const col=document.createElement('div');
   col.className='col p-lg-4 py-3';
   const poster=document.createElement('img');
   poster.className='rounded-4 shadow';
   poster.alt=offer.title||'صورة عرض سفير الحرمين';
   poster.loading='lazy';
   poster.style.cssText='display:block;width:100%;height:auto;max-height:760px;object-fit:contain';
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
 window.safirSiteOffersReceive=function(payload){
   if(!payload||payload.ok!==true||!Array.isArray(payload.offers))return;
   const offers=payload.offers.filter(function(o){return o&&o.id&&o.status==='منشور'&&o.category===category});
   offers.sort(function(a,b){
     return (Date.parse(b.created_at)||0)-(Date.parse(a.created_at)||0);
   });
   container.replaceChildren();
   offers.forEach(function(o){container.appendChild(makeCard(o))});
   host.hidden=!offers.length;
 };
 const script=document.createElement('script');
 script.async=true;
 script.src=FEED+'?format=jsonp&callback=safirSiteOffersReceive&t='+Date.now();
 script.onerror=function(){script.remove();host.hidden=true};
 document.head.append(script);
})();
